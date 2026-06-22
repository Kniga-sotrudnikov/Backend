from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from vacancies.models import Vacancy
from vacancies.serializers import VacancyAdminSerializer, VacancyBriefSerializer, VacancyDetailSerializer

from accounts.permissions import IsHR


def get_vacancy_queryset():
    """Возвращает queryset вакансий с предзагрузкой подразделения."""
    return Vacancy.objects.select_related('department', 'department__parent')


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

        department_id = self.request.query_params.get('department_id')

        if department_id:
            queryset = queryset.filter(department_id=department_id)

        status = self.request.query_params.get(
            'status',
            Vacancy.Status.OPEN,
        )

        queryset = queryset.filter(status=status)

        return queryset


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

    queryset = get_vacancy_queryset().prefetch_related('department__children')
