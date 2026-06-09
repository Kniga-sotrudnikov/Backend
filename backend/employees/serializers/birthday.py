from employees.models import Employee
from employees.utils import calculate_days_until_birthday
from rest_framework import serializers


class EmployeeBirthdayBriefSerializer(serializers.ModelSerializer):
    birthday_display = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ('id', 'full_name', 'birthday_display')

    def get_birthday_display(self, obj):
        if not obj.birthday:
            return ''
        return obj.birthday.strftime('%d.%m')


class AdminUpcomingBirthdaySerializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()
    days_until = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ('employee', 'birthday', 'days_until')

    def get_employee(self, obj):
        return {
            'id': obj.id,
            'full_name': obj.full_name,
            'photo_url': getattr(obj, 'photo_url', None),
            'department_name': obj.department.name if obj.department else None,
        }

    def get_days_until_birthday(self, obj):
        return calculate_days_until_birthday(obj.birthday)
