from rest_framework import serializers

from employees.models import Employee, InaccuracyReport
from employees.services import EmployeeCreate, EmployeeUpdate, create_employee, update_employee
from tags.models import Tag
from tags.serializers import TagSerializer
from tags.services import assign_tags, remove_tags


class TagNameField(serializers.CharField):
    """Строго принимает название тега только строкой."""

    default_error_messages = {
        **serializers.CharField.default_error_messages,
        'invalid': 'Тег должен быть строкой',
    }

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail('invalid')
        return super().to_internal_value(data)


def validate_tag_names(value):
    """Проверяет открытый список строковых тегов."""
    max_length = Tag._meta.get_field('name').max_length
    normalized_names = []

    for name in value:
        normalized_name = name.strip()
        if not normalized_name:
            raise serializers.ValidationError('Название тега не может быть пустым')
        if len(normalized_name) > max_length:
            raise serializers.ValidationError(f'Название тега не может быть длиннее {max_length} символов')
        normalized_names.append(normalized_name)

    return normalized_names


def resolve_tag_ids(tag_names):
    """Возвращает id тегов, создавая недостающие свободные теги."""
    tag_ids = []
    for name in tag_names:
        tag, _ = Tag.objects.get_or_create(name=name)
        tag_ids.append(tag.id)

    return list(dict.fromkeys(tag_ids))


def get_request_user(context):
    """Возвращает пользователя, выполнившего запрос."""
    request = context.get('request')
    if request and request.user.is_authenticated:
        return request.user
    return None


class EmployeeBriefSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source='department.name',
        read_only=True,
    )
    direction_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    birthday_display = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    supervisor_id = serializers.SerializerMethodField()
    employment_status_display = serializers.CharField(
        source='get_employment_status_display',
        read_only=True,
    )

    class Meta:
        model = Employee
        fields = (
            'id',
            'full_name',
            'job_title',
            'department_name',
            'direction_name',
            'photo_url',
            'status',
            'birthday_display',
            'tags',
            'city',
            'employment_status',
            'employment_status_display',
            'supervisor_name',
            'supervisor_id',
        )

    def get_direction_name(self, obj: Employee) -> str | None:
        direction = obj.direction
        return direction.name if direction else None

    def get_birthday_display(self, obj: Employee) -> str | None:
        if not obj.birthday:
            return None
        month = {
            1: 'января',
            2: 'февраля',
            3: 'марта',
            4: 'апреля',
            5: 'мая',
            6: 'июня',
            7: 'июля',
            8: 'августа',
            9: 'сентября',
            10: 'октября',
            11: 'ноября',
            12: 'декабря',
        }
        return f'{obj.birthday.day} {month[obj.birthday.month]}'

    def get_photo_url(self, obj: Employee) -> str | None:
        """Возвращает URL миниатюры для списков."""
        if obj.photo_thumb:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo_thumb.url)
            return obj.photo_thumb.url
        return None

    def get_tags(self, obj: Employee):
        """Возвращает только активные (неудаленные) теги."""
        active_employee_tags = getattr(obj, 'prefetched_active_employee_tags', None)
        if active_employee_tags is None:
            active_employee_tags = obj.employee_tags.filter(is_deleted=False).select_related('tag')
        tags = [employee_tag.tag for employee_tag in active_employee_tags]
        return TagSerializer(tags, many=True).data

    def get_supervisor_name(self, obj: Employee) -> str | None:
        """Возвращает имя руководителя."""
        if obj.supervisor:
            return obj.supervisor.full_name
        return None

    def get_supervisor_id(self, obj: Employee) -> int | None:
        """Возвращает ID руководителя."""
        if obj.supervisor:
            return obj.supervisor.id
        return None

    def get_employment_status_display(self, obj: Employee) -> str:
        """Возвращает человекочитаемое название статуса работы."""
        choices = dict(Employee._meta.get_field('employment_status').choices)
        return choices.get(obj.employment_status, obj.employment_status)


class EmployeeDetailSerializer(EmployeeBriefSerializer):
    """Детальный сериализатор для сотрудника."""

    role_description = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        help_text='Список ролей или обязанностей сотрудника',
    )
    supervisor_detail = serializers.SerializerMethodField()
    supervisor_role_name = serializers.CharField(
        source='supervisor_role.name',
        read_only=True,
    )
    supervisor_photo_url = serializers.SerializerMethodField()
    department_id = serializers.IntegerField(
        source='department.id',
        read_only=True,
    )
    photo_original_url = serializers.SerializerMethodField()

    class Meta(EmployeeBriefSerializer.Meta):
        fields = EmployeeBriefSerializer.Meta.fields + (
            'email',
            'phone',
            'personal_phone',
            'personal_email',
            'interests',
            'birthday',
            'role_description',
            'department',
            'department_id',
            'department_name',
            'direction_name',
            'city',
            'employment_status',
            'employment_status_display',
            'crm_profile',
            'social_network',
            'resume_link',
            'supervisor_detail',
            'supervisor_role_name',
            'supervisor_photo_url',
            'photo_original_url',
            'created_at',
            'updated_at',
        )  # type: ignore

    def get_photo_url(self, obj: Employee) -> str | None:
        """Переопределяет родительский метод для отдачи оригинала в детальной карточке."""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    def get_photo_original_url(self, obj: Employee) -> str | None:
        """Возвращает URL оригинального фото для детальной карточки."""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    def get_supervisor_detail(self, obj: Employee) -> dict | None:
        """Возвращает детальную информацию о руководителе."""
        if not obj.supervisor:
            return None

        supervisor = obj.supervisor
        return {
            'id': supervisor.id,
            'full_name': supervisor.full_name,
            'job_title': supervisor.job_title,
            'photo_url': self.get_photo_url(supervisor),
            'department_name': supervisor.department.name if supervisor.department else None,
            'department_id': supervisor.department.id if supervisor.department else None,
        }

    def get_supervisor_photo_url(self, obj: Employee) -> str | None:
        """Возвращает URL фото руководителя."""
        if obj.supervisor_photo and obj.supervisor_photo.photo_thumb:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.supervisor_photo.photo_thumb.url)
            return obj.supervisor_photo.photo_thumb.url
        return None


class EmployeeAdminDetailSerializer(EmployeeDetailSerializer):
    class Meta(EmployeeDetailSerializer.Meta):
        fields = EmployeeDetailSerializer.Meta.fields + ('created_by',)  # type: ignore


class EmployeeCreateSerializer(serializers.ModelSerializer):
    role_description = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        allow_empty=True,
        allow_null=True,
        help_text='Список ролей или обязанностей сотрудника',
    )
    tags = serializers.ListField(
        child=TagNameField(),
        write_only=True,
        required=False,
        help_text='Открытый список строковых тегов',
    )
    supervisor = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True,
    )
    supervisor_role = serializers.PrimaryKeyRelatedField(
        queryset=Employee._meta.get_field('supervisor_role').remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )
    supervisor_photo = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Employee
        fields = (
            'full_name',
            'job_title',
            'role_description',
            'email',
            'phone',
            'personal_phone',
            'personal_email',
            'interests',
            'birthday',
            'user',
            'department',
            'supervisor',
            'supervisor_role',
            'supervisor_photo',
            'city',
            'employment_status',
            'crm_profile',
            'social_network',
            'resume_link',
            'tags',
        )

    def validate_role_description(self, value):
        """Проверяет, что role_description - список строк."""
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('role_description должен быть списком строк')
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError('Все элементы role_description должны быть строками')
        return value

    def validate_tags(self, value):
        return validate_tag_names(value)

    def create(self, validated_data):
        tag_ids = resolve_tag_ids(validated_data.pop('tags', []))
        employee = create_employee(EmployeeCreate(**validated_data), created_by=get_request_user(self.context))
        if tag_ids:
            assign_tags(employee, tag_ids, by_user=get_request_user(self.context))
        return employee


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    role_description = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        allow_empty=True,
        allow_null=True,
        help_text='Список ролей или обязанностей сотрудника',
    )
    tags = serializers.ListField(
        child=TagNameField(),
        write_only=True,
        required=False,
        help_text='Открытый список строковых тегов',
    )
    supervisor = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True,
    )
    supervisor_role = serializers.PrimaryKeyRelatedField(
        queryset=Employee._meta.get_field('supervisor_role').remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )
    supervisor_photo = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Employee
        fields = (
            'full_name',
            'job_title',
            'role_description',
            'email',
            'phone',
            'personal_phone',
            'personal_email',
            'interests',
            'birthday',
            'user',
            'department',
            'supervisor',
            'supervisor_role',
            'supervisor_photo',
            'city',
            'employment_status',
            'crm_profile',
            'social_network',
            'resume_link',
            'tags',
        )

        extra_kwargs = {'tags': {'required': False}}

    def validate_role_description(self, value):
        """Проверяет, что role_description - список строк."""
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('role_description должен быть списком строк')
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError('Все элементы role_description должны быть строками')
        return value

    def validate_tags(self, value):
        return validate_tag_names(value)

    def update(self, instance, validated_data):
        tag_names = validated_data.pop('tags', None)
        user = get_request_user(self.context)
        employee = update_employee(
            instance,
            EmployeeUpdate(**validated_data),
            updated_by=user,
        )
        if tag_names is not None:
            tag_ids = resolve_tag_ids(tag_names)
            current_tag_ids = set(employee.employee_tags.filter(is_deleted=False).values_list('tag_id', flat=True))
            new_tag_ids = set(tag_ids)
            add_ids = list(new_tag_ids - current_tag_ids)
            remove_ids = list(current_tag_ids - new_tag_ids)
            if add_ids:
                assign_tags(employee, add_ids, by_user=user)
            if remove_ids:
                remove_tags(employee, remove_ids, by_user=user)
            if hasattr(employee, 'prefetched_active_employee_tags'):
                delattr(employee, 'prefetched_active_employee_tags')
        return employee


class InaccuracyReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InaccuracyReport
        fields = ('message',)


class InaccuracyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = InaccuracyReport
        fields = (
            'id',
            'employee_id',
            'message',
            'created_at',
            'status',
        )
