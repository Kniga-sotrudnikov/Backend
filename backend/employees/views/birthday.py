from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR
from employees.models import Employee
from employees.serializers.birthday import AdminUpcomingBirthdaySerializer, EmployeeBirthdayBriefSerializer
from employees.utils import calculate_days_until_birthday, get_birthday_days_condition


class EmployeeBirthdaysAPIView(APIView):
    """E5: Публичный эндпоинт ближайших ДР сотрудников."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 7))
        except ValueError:
            days_ahead = 7

        pairs = get_birthday_days_condition(days_ahead)

        # Фильтруем только активных и не удаленных сотрудников
        queryset = Employee.objects.filter(status='active', is_deleted=False)

        # Строим ORM-запрос для комбинаций (месяц, день)
        matched_employees = []
        for emp in queryset:
            if emp.birthday and (emp.birthday.month, emp.birthday.day) in pairs:
                matched_employees.append(emp)

        serializer = EmployeeBirthdayBriefSerializer(matched_employees, many=True)
        return Response(serializer.data)


class AdminUpcomingBirthdaysAPIView(APIView):
    """AB1: Админский эндпоинт ближайших ДР для HR."""

    permission_classes = (IsHR,)

    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 30))
        except ValueError:
            days_ahead = 30

        pairs = get_birthday_days_condition(days_ahead)
        queryset = Employee.objects.filter(status='active', is_deleted=False)

        matched_employees = []
        for emp in queryset:
            if emp.birthday and (emp.birthday.month, emp.birthday.day) in pairs:
                emp.days_until = calculate_days_until_birthday(emp.birthday)
                matched_employees.append(emp)

        # сортировка по days_until
        matched_employees.sort(key=lambda x: x.days_until)

        serializer = AdminUpcomingBirthdaySerializer(matched_employees, many=True)
        return Response(serializer.data)
