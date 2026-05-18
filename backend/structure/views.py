from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt import models

from .models import Department
from .serializers import DepartmentBriefSerializer, DepartmentDetailSerializer, OrgTreeNodeSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """Управление подразделениями с ручной фильтрацией параметров."""

    def get_queryset(self):
        queryset = Department.objects.active()

        # Получаем параметры из self.request.query_params
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
        instance.delete(user=self.request.user)


class DirectionListView(generics.ListAPIView):
    """Только направления верхнего уровня (parent_id is null)."""

    queryset = Department.objects.active().filter(parent__isnull=True)
    serializer_class = DepartmentBriefSerializer


class OrgStructureTreeView(APIView):
    """
    Эндпоинт для получения полного дерева организации.

    Начинает построение с объектов верхнего уровня (направлений).
    """

    def get(self, request, *args, **kwargs):
        roots = (
            Department.objects.active()
            .filter(parent__isnull=True)
            .prefetch_related(
                models.Prefetch('children', queryset=Department.objects.active(), to_attr='prefetched_children')
            )
        )

        serializer = OrgTreeNodeSerializer(roots, many=True)
        return Response(serializer.data)
