from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from vacancies.models import Vacancy

from accounts.permissions import IsHR
from core.serializers import AdminSummarySerializer
from employees.models import Employee, Status
from structure.models import Department


class AdminSummaryView(APIView):
    """Счётчики для шапки административного интерфейса."""

    permission_classes = (IsHR,)

    @extend_schema(
        summary='Счётчики административного интерфейса',
        description='Возвращает агрегированные количества для шапки админки.',
        responses={200: AdminSummarySerializer},
    )
    def get(self, request):
        data = {
            'employees_count': Employee.objects.filter(status=Status.ACTIVE).count(),
            'directions_count': Department.objects.filter(type=Department.Type.DIRECTION, is_active=True).count(),
            'vacancies_count': Vacancy.objects.filter(status=Vacancy.Status.OPEN).count(),
        }
        return Response(AdminSummarySerializer(data).data)
