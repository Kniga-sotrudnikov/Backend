from rest_framework import serializers

from employees.models import Employee
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
        active_employee_tags = obj.employee_tags.filter(is_deleted=False).select_related('tag')
        tags = [employee_tag.tag for employee_tag in active_employee_tags]
        return TagSerializer(tags, many=True).data


class EmployeeDetailSerializer(EmployeeBriefSerializer):
    class Meta(EmployeeBriefSerializer.Meta):
        fields = EmployeeBriefSerializer.Meta.fields + (
            'email',
            'phone',
            'interests',
            'birthday',
            'role_description',
            'department',
        )  # type: ignore

    def get_photo_url(self, obj: Employee) -> str | None:
        """Переопределяет родительский метод для отдачи оригинала в детальной карточке."""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
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

    class Meta:
        model = Employee
        fields = (
            'full_name',
            'job_title',
            'role_description',
            'email',
            'phone',
            'interests',
            'birthday',
            'user',
            'department',
            'tags',
        )

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

    class Meta:
        model = Employee
        fields = (
            'full_name',
            'job_title',
            'role_description',
            'email',
            'phone',
            'interests',
            'birthday',
            'user',
            'department',
            'tags',
        )

        extra_kwargs = {'tags': {'required': False}}

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
