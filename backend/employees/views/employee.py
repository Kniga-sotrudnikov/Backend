from typing import cast

from employees.models import Employee, Status
from employees.serializers.employee import (
    EmployeeAdminDetailSerializer,
    EmployeeBriefSerializer,
    EmployeeCreateSerializer,
    EmployeeDetailSerializer,
    EmployeeUpdateSerializer,
)
from employees.services import archive_employee
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet


class EmployeeViewSet(ReadOnlyModelViewSet):
    def get_queryset(self):
        return (
            Employee.objects.active()
            .filter(status=Status.ACTIVE)
            .select_related('department', 'department__parent')
            .prefetch_related('employee_tags__tag')
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EmployeeDetailSerializer
        return EmployeeBriefSerializer


class EmployeeAdminViewSet(ModelViewSet):
    queryset = Employee.objects.all()

    def get_queryset(self):
        queryset = Employee.objects.select_related('department', 'department__parent').prefetch_related(
            'employee_tags__tag'
        )
        if self.request.query_params.get('status') == Status.ARCHIVED:
            return queryset.filter(status=Status.ARCHIVED)
        return queryset.filter(status=Status.ACTIVE)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        employee = cast(Employee, self.get_object())
        archive_employee(employee=employee, updated_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        match self.action:
            case 'list':
                return EmployeeBriefSerializer
            case 'retrieve':
                return EmployeeAdminDetailSerializer
            case 'create':
                return EmployeeCreateSerializer
            case 'update' | 'partial_update':
                return EmployeeUpdateSerializer
            case _:
                return EmployeeAdminDetailSerializer
