from functools import reduce
from operator import or_

from django.db.models import Q
from django.db.models.functions import ExtractDay, ExtractMonth
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR
from employees.models import Employee
from employees.serializers.birthday import AdminUpcomingBirthdaySerializer, EmployeeBirthdayBriefSerializer
from employees.utils import calculate_days_until_birthday, get_birthday_days_condition


def get_upcoming_birthdays_queryset(days_ahead: int):
    """Возвращает queryset сотрудников с ближайшими днями рождения."""
    pairs = get_birthday_days_condition(days_ahead)
    date_filters = [Q(birthday_month=month, birthday_day=day) for month, day in pairs]
    birthday_filter = reduce(or_, date_filters, Q())

    return (
        Employee.objects.filter(status='active', is_deleted=False)
        .select_related('department')
        .annotate(
            birthday_month=ExtractMonth('birthday'),
            birthday_day=ExtractDay('birthday'),
        )
        .filter(birthday_filter)
    )


class EmployeeBirthdaysAPIView(APIView):
    """E5: Публичный эндпоинт ближайших ДР сотрудников."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 7))
        except ValueError:
            days_ahead = 7

        queryset = get_upcoming_birthdays_queryset(days_ahead)
        serializer = EmployeeBirthdayBriefSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminUpcomingBirthdaysAPIView(APIView):
    """AB1: Админский эндпоинт ближайших ДР для HR."""

    permission_classes = (IsHR,)

    def get(self, request):
        try:
            days_ahead = int(request.query_params.get('days_ahead', 30))
        except ValueError:
            days_ahead = 30

        matched_employees = list(get_upcoming_birthdays_queryset(days_ahead))
        for emp in matched_employees:
            emp.days_until = calculate_days_until_birthday(emp.birthday)

        # сортировка по days_until
        matched_employees.sort(key=lambda x: x.days_until)

        serializer = AdminUpcomingBirthdaySerializer(matched_employees, many=True)
        return Response(serializer.data)
