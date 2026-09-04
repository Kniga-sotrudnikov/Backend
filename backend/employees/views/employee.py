import logging
from typing import cast

from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from notifications.tasks import notify_hr_about_inaccuracy_report
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from accounts.permissions import IsHR
from core.xlsx import build_xlsx
from employees.models import Employee, EmploymentStatus, Status
from employees.serializers.employee import (
    BulkActionRequestSerializer,
    BulkActionResponseSerializer,
    EmployeeAdminDetailSerializer,
    EmployeeBriefSerializer,
    EmployeeCreateSerializer,
    EmployeeDetailSerializer,
    EmployeeUpdateSerializer,
    InaccuracyReportCreateSerializer,
    InaccuracyReportSerializer,
)
from employees.services import archive_employee
from structure.models import Department
from tags.models import EmployeeTag, Tag

ALLOWED_ORDERING_FIELDS = ('full_name', '-full_name', 'birthday', '-birthday')
XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
logger = logging.getLogger(__name__)

EMPLOYEE_LIST_FILTER_PARAMETERS = [
    OpenApiParameter(
        'limit',
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        required=False,
        description='Лимит пагинации.',
    ),
    OpenApiParameter(
        'offset',
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        required=False,
        description='Смещение пагинации.',
    ),
    OpenApiParameter(
        'search',
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        description='Поиск по full_name и job_title.',
    ),
    OpenApiParameter(
        'tag',
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        required=False,
        many=True,
        description='ID тега. Можно передавать несколько раз: ?tag=1&tag=2.',
    ),
    OpenApiParameter(
        'job_title',
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        description='Фильтр по точному совпадению должности.',
    ),
    OpenApiParameter(
        'department_id',
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        required=False,
        description='ID отдела.',
    ),
    OpenApiParameter(
        'direction_id',
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        required=False,
        description='ID направления.',
    ),
    OpenApiParameter(
        'city',
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        description='Фильтр по городу, точное совпадение без учета регистра.',
    ),
    OpenApiParameter(
        'employment_status',
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        enum=EmploymentStatus.values,
        description='Статус работы сотрудника.',
    ),
    OpenApiParameter(
        'ordering',
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        enum=ALLOWED_ORDERING_FIELDS,
        description='Сортировка по full_name или birthday.',
    ),
]

ADMIN_EMPLOYEE_LIST_FILTER_PARAMETERS = [
    OpenApiParameter(
        'status',
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        enum=[Status.ACTIVE, Status.ARCHIVED],
        description='Статус карточки. Архивные сотрудники доступны только в HR-ручках.',
    ),
    *EMPLOYEE_LIST_FILTER_PARAMETERS,
]


def get_employee_queryset():
    """Возвращает базовый queryset сотрудников с предзагрузкой связанных объектов."""
    active_tags_prefetch = Prefetch(
        'employee_tags',
        queryset=EmployeeTag.objects.filter(is_deleted=False).select_related('tag'),
        to_attr='prefetched_active_employee_tags',
    )
    return Employee.objects.select_related(
        'department',
        'department__parent',
        'user',
        'supervisor',
        'supervisor__department',
        'supervisor__department__parent',
        'supervisor_role',
        'supervisor_photo',
        'supervisor_photo__department',
        'supervisor_photo__department__parent',
    ).prefetch_related(active_tags_prefetch)


def apply_employee_filters(queryset, request: Request, allow_archived: bool = False):
    """Применяет фильтры, поиск и сортировку к queryset сотрудников.

    Поддерживает фильтрацию по status, tag, job_title, department_id,
    direction_id, city, employment_status, поиск по подстроке в full_name
    и job_title, а также сортировку по full_name и birthday.

    Args:
        queryset: Базовый queryset сотрудников.
        request: HTTP-запрос с query params.
        allow_archived: Разрешает фильтрацию по archived для admin-списка.
    """
    params = request.query_params
    status = params.get('status')
    search = params.get('search')
    tag_ids = params.getlist('tag')
    job_title = params.get('job_title')
    department_id = params.get('department_id')
    direction_id = params.get('direction_id')
    city = params.get('city')
    employment_status = params.get('employment_status')
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
    if city:
        queryset = queryset.filter(city__iexact=city)
    if employment_status:
        queryset = queryset.filter(employment_status=employment_status)
    queryset = queryset.distinct()
    if ordering in ALLOWED_ORDERING_FIELDS:
        return queryset.order_by(ordering)
    return queryset


@extend_schema_view(
    list=extend_schema(
        summary='Публичный список сотрудников',
        description=(
            'Возвращает только активных сотрудников. Даже если передать status=archived, '
            'архивные сотрудники не попадут в ответ.'
        ),
        parameters=EMPLOYEE_LIST_FILTER_PARAMETERS,
    )
)
class EmployeeViewSet(ReadOnlyModelViewSet):
    def get_queryset(self):
        return apply_employee_filters(get_employee_queryset(), self.request)

    def get_serializer_class(self):
        match self.action:
            case 'retrieve':
                return EmployeeDetailSerializer
            case 'report_inaccuracy':
                return InaccuracyReportCreateSerializer
            case _:
                return EmployeeBriefSerializer

    @extend_schema(
        summary='Сообщить о неточности в карточке сотрудника',
        description='Доступно всем авторизованным пользователям.',
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(response=InaccuracyReportSerializer),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description='Сотрудник не найден'),
        },
    )
    @action(detail=True, methods=['post'], url_path='report-inaccuracy')
    def report_inaccuracy(self, request: Request, pk=None) -> Response:
        employee = cast(Employee, self.get_object())
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(employee=employee, created_by=request.user)
        transaction.on_commit(lambda: self._enqueue_inaccuracy_report_notification(report.id))
        return Response(InaccuracyReportSerializer(report).data, status=status.HTTP_201_CREATED)

    def _enqueue_inaccuracy_report_notification(self, report_id: int) -> None:
        try:
            notify_hr_about_inaccuracy_report.delay(report_id)
        except Exception:
            logger.exception(f'Ошибка постановки в очередь уведомления HR о неточности в карточке {report_id}')


@extend_schema_view(
    list=extend_schema(
        summary='Административный список сотрудников',
        description='Возвращает сотрудников для таблицы админки с фильтрами и сортировкой.',
        parameters=ADMIN_EMPLOYEE_LIST_FILTER_PARAMETERS,
    ),
    create=extend_schema(
        summary='Создать сотрудника',
        description='Сотрудник добавляется в отдел через поле department, куда передается ID отдела.',
        request=EmployeeCreateSerializer,
        responses={status.HTTP_201_CREATED: EmployeeAdminDetailSerializer},
        examples=[
            OpenApiExample(
                'Создание сотрудника в отделе',
                value={
                    'full_name': 'Иван Иванов',
                    'job_title': 'Backend Developer',
                    'email': 'ivan@example.com',
                    'birthday': '1990-01-01',
                    'department': 10,
                    'city': 'Москва',
                    'employment_status': EmploymentStatus.WORKING,
                    'tags': ['Python', 'Django'],
                },
                request_only=True,
            )
        ],
    ),
    partial_update=extend_schema(
        summary='Частично обновить сотрудника',
        description='Для переноса сотрудника в другой отдел передайте ID нового отдела в поле department.',
        request=EmployeeUpdateSerializer,
        responses={status.HTTP_200_OK: EmployeeAdminDetailSerializer},
        examples=[
            OpenApiExample(
                'Перенос сотрудника в другой отдел',
                value={'department': 11},
                request_only=True,
            )
        ],
    ),
)
class EmployeeAdminViewSet(ModelViewSet):
    permission_classes = [IsHR]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

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

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        headers = self.get_success_headers(serializer.data)
        response_serializer = EmployeeAdminDetailSerializer(employee, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        employee = self.get_object()
        serializer = self.get_serializer(employee, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        response_serializer = EmployeeAdminDetailSerializer(employee, context=self.get_serializer_context())
        return Response(response_serializer.data)

    def get_serializer_class(self):
        match self.action:
            case 'list':
                return EmployeeBriefSerializer
            case 'retrieve':
                return EmployeeAdminDetailSerializer
            case 'create':
                return EmployeeCreateSerializer
            case 'partial_update':
                return EmployeeUpdateSerializer
            case _:
                return EmployeeAdminDetailSerializer

    @extend_schema(
        summary='Экспорт сотрудников в Excel',
        description='Выгружает сотрудников в XLSX с учётом фильтров и сортировки списка.',
        parameters=ADMIN_EMPLOYEE_LIST_FILTER_PARAMETERS,
        responses={200: OpenApiResponse(response=OpenApiTypes.BINARY, description='XLSX-файл')},
    )
    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request: Request) -> HttpResponse:
        queryset = apply_employee_filters(get_employee_queryset(), request, allow_archived=True)
        headers = [
            'ID',
            'ФИО',
            'Должность',
            'Email',
            'Телефон',
            'Отдел',
            'Направление',
            'Статус карточки',
            'Статус занятости',
            'Дата рождения',
            'Город',
        ]
        rows = [
            [
                employee.id,
                employee.full_name,
                employee.job_title,
                employee.email,
                employee.phone,
                employee.department.name if employee.department else '',
                employee.direction.name if employee.direction else '',
                employee.status,
                employee.get_employment_status_display(),
                employee.birthday,
                employee.city,
            ]
            for employee in queryset
        ]
        response = HttpResponse(build_xlsx(headers, rows, sheet_name='Сотрудники'), content_type=XLSX_CONTENT_TYPE)
        response['Content-Disposition'] = 'attachment; filename="employees.xlsx"'
        return response

    @extend_schema(
        summary='Массовое действие над сотрудниками',
        description=(
            'Поддерживает действия archive, add_tag, remove_tag и change_department. '
            'Для add_tag/remove_tag передайте params.tag, для change_department - params.department_id.'
        ),
        request=BulkActionRequestSerializer,
        responses={status.HTTP_200_OK: BulkActionResponseSerializer},
        examples=[
            OpenApiExample(
                'Массовый перенос сотрудников',
                value={
                    'employee_ids': [1, 2, 3],
                    'action': 'change_department',
                    'params': {'department_id': 10},
                },
                request_only=True,
            ),
            OpenApiExample(
                'Массовое добавление тега',
                value={
                    'employee_ids': [1, 2, 3],
                    'action': 'add_tag',
                    'params': {'tag': 7},
                },
                request_only=True,
            ),
            OpenApiExample(
                'Массовое удаление тега',
                value={
                    'employee_ids': [1, 2, 3],
                    'action': 'remove_tag',
                    'params': {'tag': 7},
                },
                request_only=True,
            ),
            OpenApiExample(
                'Массовая архивация',
                value={
                    'employee_ids': [1, 2, 3],
                    'action': 'archive',
                    'params': {},
                },
                request_only=True,
            ),
            OpenApiExample(
                'Результат массового действия',
                value={'total': 3, 'success': 3, 'failed': 0, 'details': []},
                response_only=True,
            ),
        ],
    )
    @action(detail=False, methods=['post'], url_path='bulk-action')
    def bulk_action(self, request: Request) -> Response:
        employee_ids = request.data.get('employee_ids', [])
        action_name = request.data.get('action')
        params = request.data.get('params', {})
        results: dict = {'total': len(employee_ids), 'success': 0, 'failed': 0, 'details': []}
        for emp_id in employee_ids:
            try:
                with transaction.atomic():
                    self.apply_bulk_action(emp_id, action_name, params, request)
                results['success'] += 1
            except Exception as exc:
                results['failed'] += 1
                results['details'].append({'employee_id': emp_id, 'error': str(exc)})
        return Response(results)

    def apply_bulk_action(self, emp_id: int, action_name: str, params: dict, request: Request) -> None:
        employee = Employee.objects.get(pk=emp_id)
        match action_name:
            case 'archive':
                archive_employee(employee=employee, updated_by=request.user)
            case 'add_tag':
                tag = Tag.objects.get(pk=params['tag'])
                EmployeeTag.objects.get_or_create(tag=tag, employee=employee, defaults={'assigned_by': request.user})
            case 'remove_tag':
                tag = Tag.objects.get(pk=params['tag'])
                EmployeeTag.objects.filter(tag=tag, employee=employee).delete()
            case 'change_department':
                department = Department.objects.get(pk=params['department_id'])
                employee.department = department
                employee.updated_by = request.user
                employee.save(update_fields=['department', 'updated_by'])
            case _:
                raise ValueError(f'Неизвестное действие: {action_name}')
