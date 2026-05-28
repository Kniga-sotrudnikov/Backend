from employees.models import Employee
from employees.services import EmployeeCreate, EmployeeUpdate, create_employee, update_employee
from rest_framework import serializers
from tags.serializers import TagSerializer
from tags.services import assign_tags



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

    def get_photo_url(self, obj: Employee):
        return None

    def get_tags(self, obj: Employee):
        return TagSerializer([employee_tag.tag for employee_tag in obj.employee_tags.all()], many=True).data


class EmployeeDetailSerializer(EmployeeBriefSerializer):
    class Meta(EmployeeBriefSerializer.Meta):
        fields = EmployeeBriefSerializer.Meta.fields + (
            'email',
            'phone',
            'interests',
            'birthday',
            'role_description',
            'department',
        )


class EmployeeAdminDetailSerializer(EmployeeDetailSerializer):
    class Meta(EmployeeDetailSerializer.Meta):
        fields = EmployeeDetailSerializer.Meta.fields + (
            'created_at',
            'updated_at',
            'created_by',
        )


class EmployeeCreateSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

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

    def create(self, validated_data):
        tag_ids = validated_data.pop('tags', [])
        employee = create_employee(EmployeeCreate(**validated_data), created_by=get_request_user(self.context))
        assign_tags(employee, tag_ids, by_user=get_request_user(self.context))
        return employee


class EmployeeUpdateSerializer(serializers.ModelSerializer):
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
        )

    def update(self, instance, validated_data):
        return update_employee(
            instance,
            EmployeeUpdate(**validated_data),
            updated_by=get_request_user(self.context),
        )
