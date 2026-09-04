from django.db.models import Q
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from vacancies.models import Vacancy
from vacancies.serializers import VacancyAdminSerializer, VacancyBriefSerializer, VacancyDetailSerializer

from accounts.permissions import IsHR
from core.xlsx import build_xlsx

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

ALLOWED_VACANCY_ORDERING_FIELDS = ('title', '-title', 'created_at', '-created_at', 'status', '-status')


def get_vacancy_queryset():
    """Возвращает queryset вакансий с предзагрузкой подразделения."""
    return Vacancy.objects.select_related('department', 'department__parent')


def apply_vacancy_filters(queryset, request, default_status: str | None = None):
    """Применяет фильтры и сортировку к queryset вакансий."""
    department_id = request.query_params.get('department_id')
    status = request.query_params.get('status', default_status)
    search = request.query_params.get('search')
    ordering = request.query_params.get('ordering')

    if department_id:
        queryset = queryset.filter(department_id=department_id)
    if status:
        queryset = queryset.filter(status=status)
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if ordering in ALLOWED_VACANCY_ORDERING_FIELDS:
        queryset = queryset.order_by(ordering)
    return queryset


@extend_schema(
    parameters=[
        OpenApiParameter(
            name='department_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
        ),
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=['open', 'closed'],
        ),
    ]
)
class VacancyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """
    Public API для работы с вакансиями.

    Поддерживает:
        - получение списка вакансий (с фильтрами)
        - получение детальной информации о вакансии

    Ограничения:
        - доступ только для авторизованных пользователей

    Endpoints:
        GET /api/v1/vacancies/
        GET /api/v1/vacancies/{id}/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VacancyDetailSerializer
        return VacancyBriefSerializer

    def get_queryset(self):
        queryset = get_vacancy_queryset()
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('department__children')

        return apply_vacancy_filters(queryset, self.request, default_status=Vacancy.Status.OPEN)


@extend_schema_view(
    list=extend_schema(
        summary='Административный список вакансий',
        description='Возвращает вакансии для таблицы админки с фильтрами и сортировкой.',
        parameters=[
            OpenApiParameter('department_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                'status',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=False,
                enum=[Vacancy.Status.OPEN, Vacancy.Status.CLOSED],
            ),
            OpenApiParameter('search', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                'ordering',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=False,
                enum=ALLOWED_VACANCY_ORDERING_FIELDS,
            ),
        ],
    )
)
class VacancyAdminViewSet(ModelViewSet):
    """
    Административный API для управления вакансиями.

    Доступ:
        - только пользователи с правами HR (IsHR)

    Возможности:
        - создание вакансий
        - редактирование вакансий
        - удаление вакансий (soft delete через модель)
        - просмотр всех вакансий (включая закрытые)

    Endpoints:
        /api/v1/admin/vacancies/
        /api/v1/admin/vacancies/{id}/
    """

    http_method_names = [
        'get',
        'post',
        'patch',
        'delete',
        'head',
        'options',
    ]

    permission_classes = [IsHR]

    serializer_class = VacancyAdminSerializer

    def get_queryset(self):
        queryset = get_vacancy_queryset().prefetch_related('department__children')
        if self.action in ('list', 'export'):
            return apply_vacancy_filters(queryset, self.request)
        return queryset

    @extend_schema(
        summary='Экспорт вакансий в Excel',
        description='Выгружает вакансии в XLSX с учётом фильтров.',
        parameters=[
            OpenApiParameter(
                name='department_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=['open', 'closed'],
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: OpenApiResponse(response=OpenApiTypes.BINARY, description='XLSX-файл')},
    )
    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request) -> HttpResponse:
        queryset = self.get_queryset()
        headers = [
            'ID',
            'Название',
            'Отдел',
            'Направление',
            'Описание',
            'Статус',
            'Создана',
            'Обновлена',
        ]
        rows = [
            [
                vacancy.id,
                vacancy.title,
                vacancy.department.name if vacancy.department else '',
                vacancy.department.parent.name if vacancy.department and vacancy.department.parent else '',
                vacancy.description,
                vacancy.status,
                vacancy.created_at,
                vacancy.updated_at,
            ]
            for vacancy in queryset
        ]
        response = HttpResponse(build_xlsx(headers, rows, sheet_name='Вакансии'), content_type=XLSX_CONTENT_TYPE)
        response['Content-Disposition'] = 'attachment; filename="vacancies.xlsx"'
        return response
