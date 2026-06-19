from rest_framework import serializers

from employees.models import Employee, InaccuracyReport
from employees.services import EmployeeCreate, EmployeeUpdate, create_employee, update_employee
from tags.models import Tag
from tags.serializers import TagSerializer
from tags.services import assign_tags, remove_tags


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
        fields = EmployeeBriefSerializer.Meta.fields + (
            'email',
            'phone',
            'interests',
            'birthday',
            'role_description',
            'department',
            'created_at',
            'updated_at',
            'created_by',
        )  # type: ignore


class EmployeeCreateSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
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
        """Проверяет, что все теги существуют."""
        if not value:
            return value

        existing_tags = set(Tag.objects.filter(id__in=value).values_list('id', flat=True))
        missing_tags = set(value) - existing_tags

        if missing_tags:
            raise serializers.ValidationError(f'Теги с id {list(missing_tags)} не существуют')
        return value

    def create(self, validated_data):
        tag_ids = validated_data.pop('tags', [])
        employee = create_employee(EmployeeCreate(**validated_data), created_by=get_request_user(self.context))
        if tag_ids:
            assign_tags(employee, tag_ids, by_user=get_request_user(self.context))
        return employee


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
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

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tags', None)
        user = get_request_user(self.context)
        employee = update_employee(
            instance,
            EmployeeUpdate(**validated_data),
            updated_by=user,
        )
        if tag_ids is not None:
            current_tag_ids = set(employee.employee_tags.filter(is_deleted=False).values_list('tag_id', flat=True))
            new_tag_ids = set(tag_ids)
            add_ids = list(new_tag_ids - current_tag_ids)
            remove_ids = list(current_tag_ids - new_tag_ids)
            if add_ids:
                assign_tags(employee, add_ids, by_user=user)
            if remove_ids:
                remove_tags(employee, remove_ids, by_user=user)
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
