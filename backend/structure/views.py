from django.db.models import Count, Prefetch, QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR
from core.constants import READ_ROLES, STRUCTURE_TAG, WRITE_ROLES
from structure.models import Department
from structure.serializers import DepartmentBriefSerializer, DepartmentDetailSerializer, OrgTreeNodeSerializer


def get_department_queryset() -> QuerySet[Department]:
    """Базовый queryset подразделений с аннотацией количества сотрудников."""
    return Department.objects.annotate(employee_count=Count('employees', distinct=True))


@extend_schema_view(
    list=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Список подразделений',
        description=READ_ROLES,
    ),
    create=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Создание подразделения',
        description=WRITE_ROLES,
    ),
    retrieve=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Подробности подразделения',
        description=READ_ROLES,
    ),
    partial_update=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Частичное обновление подразделения',
        description=WRITE_ROLES,
    ),
    destroy=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Удаление подразделения',
        description=WRITE_ROLES,
    ),
)
class DepartmentViewSet(viewsets.ModelViewSet):
    """Управление подразделениями с ручной фильтрацией параметров."""

    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = get_department_queryset()

        dept_type = self.request.query_params.get('type')
        parent_id = self.request.query_params.get('parent_id')

        if dept_type:
            queryset = queryset.filter(type=dept_type)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DepartmentDetailSerializer
        return DepartmentBriefSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsHR()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        instance.delete()


@extend_schema(
    tags=[STRUCTURE_TAG],
    summary='Список направлений верхнего уровня',
    description=READ_ROLES,
)
class DirectionListView(generics.ListAPIView):
    """Только направления верхнего уровня (parent_id is null)."""

    queryset = get_department_queryset().filter(parent__isnull=True)
    serializer_class = DepartmentBriefSerializer


@extend_schema(
    tags=[STRUCTURE_TAG],
    summary='Дерево организационной структуры',
    description=READ_ROLES,
)
class OrgStructureTreeView(APIView):
    """Полное дерево организации, начиная с направлений верхнего уровня."""

    def get(self, request, *args, **kwargs):
        children_queryset = get_department_queryset()
        roots = (
            get_department_queryset()
            .filter(parent__isnull=True)
            .prefetch_related(Prefetch('children', queryset=children_queryset, to_attr='prefetched_children'))
        )

        serializer = OrgTreeNodeSerializer(roots, many=True)
        return Response(serializer.data)
