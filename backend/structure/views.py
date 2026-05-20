from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from core.constants import READ_ROLES, STRUCTURE_TAG, WRITE_ROLES
from structure.models import Department
from structure.serializers import DepartmentBriefSerializer, DepartmentDetailSerializer, OrgTreeNodeSerializer


@extend_schema_view(
    list=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Список подразделений',
        description=READ_ROLES,
    ),
    create=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Создание подразделения',
        description=READ_ROLES,
    ),
    retrieve=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Подробности подразделения',
        description=READ_ROLES,
    ),
    update=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Полное обновление подразделения',
        description=READ_ROLES,
    ),
    partial_update=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Частичное обновление подразделения',
        description=READ_ROLES,
    ),
    destroy=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Удаление подразделения',
        description=READ_ROLES,
    ),
)
class DepartmentViewSet(viewsets.ModelViewSet):
    """Управление подразделениями с ручной фильтрацией параметров."""

    def get_queryset(self):
        queryset = Department.objects.active()

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

    def perform_destroy(self, instance):
        instance.delete()


@extend_schema(
    tags=[WRITE_ROLES],
    summary='Список направлений верхнего уровня',
    description=READ_ROLES,
)
class DirectionListView(generics.ListAPIView):
    """Только направления верхнего уровня (parent_id is null)."""

    queryset = Department.objects.active().filter(parent__isnull=True)
    serializer_class = DepartmentBriefSerializer


@extend_schema(
    tags=[STRUCTURE_TAG],
    summary='Дерево организационной структуры',
    description=READ_ROLES,
)
class OrgStructureTreeView(APIView):
    """Полное дерево организации, начиная с направлений верхнего уровня."""

    def get(self, request, *args, **kwargs):
        roots = (
            Department.objects.active()
            .filter(parent__isnull=True)
            .prefetch_related(Prefetch('children', queryset=Department.objects.active(), to_attr='prefetched_children'))
        )

        serializer = OrgTreeNodeSerializer(roots, many=True)
        return Response(serializer.data)
