from employees.models import Employee
from rest_framework import serializers

# from tags.serializers import TagSerializer


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

    def get_photo_url(self):
        return None

    def get_tags(self): ...
