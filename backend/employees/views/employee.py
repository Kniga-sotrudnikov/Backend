from typing import cast

from django.db.models import Q
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

from accounts.permissions import IsHR

ALLOWED_ORDERING_FIELDS = ('full_name', '-full_name', 'birthday', '-birthday')


def get_employee_queryset():
    return (
        Employee.objects.filter(status=Status.ACTIVE)
        .select_related('department', 'department__parent', 'user')
        .prefetch_related('employee_tags__tag')
    )


def apply_employee_filters(queryset, request: Request, allow_archived: bool = False):
    params = request.query_params
    status = params.get('status')
    search = params.get('search')
    tag_ids = params.getlist('tag')
    job_title = params.get('job_title')
    department_id = params.get('department_id')
    direction_id = params.get('direction_id')
    ordering = params.get('ordering')
    if allow_archived and status == Status.ARCHIVED:
        queryset = queryset.filter(status=Status.ARCHIVED)
    else:
        queryset = queryset.filter(status=Status.ACTIVE)
    if search:
        queryset = queryset.filter(Q(full_name__icontains=search) | Q(job_title__icontains=search))
    if tag_ids:
        queryset = queryset.filter(employee_tags__tag_id__in=tag_ids)
    if job_title:
        queryset = queryset.filter(job_title=job_title)
    if department_id:
        queryset = queryset.filter(department_id=department_id)
    if direction_id:
        queryset = queryset.filter(department__parent_id=direction_id)
    queryset = queryset.distinct()
    if ordering in ALLOWED_ORDERING_FIELDS:
        return queryset.order_by(ordering)
    return queryset


class EmployeeViewSet(ReadOnlyModelViewSet):
    def get_queryset(self):
        return apply_employee_filters(get_employee_queryset(), self.request)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EmployeeDetailSerializer
        return EmployeeBriefSerializer


class EmployeeAdminViewSet(ModelViewSet):
    permission_classes = [IsHR]

    def get_queryset(self):
        queryset = get_employee_queryset()
        if self.action == 'list':
            return apply_employee_filters(
                queryset,
                self.request,
                allow_archived=True,
            )
        return queryset

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
