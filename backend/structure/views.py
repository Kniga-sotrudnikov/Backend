from collections import defaultdict

from django.db.models import Count, Prefetch, Q, QuerySet
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR
from core.constants import READ_ROLES, STRUCTURE_TAG, WRITE_ROLES
from structure.models import Department, OrgStructureImage
from structure.serializers import (
    DepartmentBriefSerializer,
    DepartmentDetailSerializer,
    OrgStructureImageSerializer,
    OrgStructureImageUploadSerializer,
    OrgTreeNodeSerializer,
)


def get_department_queryset() -> QuerySet[Department]:
    """Базовый queryset подразделений с аннотацией числа активных сотрудников."""
    return Department.objects.select_related('parent', 'head').annotate(
        employee_count=Count(
            'employees',
            filter=Q(employees__status='active', employees__is_deleted=False),
            distinct=True,
        )
    )


@extend_schema_view(
    list=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Список подразделений',
        description=READ_ROLES,
    ),
    create=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Создание подразделения',
        description=(
            f'{WRITE_ROLES}\n\n'
            'Поле parent принимает ID родительского направления или подразделения. '
            'Для отдела type=department нужно передать parent; для направления верхнего уровня parent может быть null.'
        ),
        request=DepartmentDetailSerializer,
        responses={status.HTTP_201_CREATED: DepartmentDetailSerializer},
        examples=[
            OpenApiExample(
                'Создание отдела внутри направления',
                value={
                    'name': 'Backend',
                    'short_name': 'BE',
                    'description': 'Backend-разработка',
                    'type': Department.Type.DEPARTMENT,
                    'parent': 123,
                    'head_id': 45,
                    'display_order': 10,
                    'is_active': True,
                },
                request_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Подробности подразделения',
        description=READ_ROLES,
    ),
    partial_update=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Частичное обновление подразделения',
        description=(
            f'{WRITE_ROLES}\n\n'
            'Чтобы изменить родителя отдела, передайте ID направления или подразделения в поле parent. '
            'Для направления верхнего уровня parent можно передать null.'
        ),
        request=DepartmentDetailSerializer,
        responses={status.HTTP_200_OK: DepartmentDetailSerializer},
        examples=[
            OpenApiExample(
                'Перенос отдела в другое направление',
                value={'parent': 123},
                request_only=True,
            )
        ],
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
        if self.action == 'retrieve':
            children_queryset = get_department_queryset()
            queryset = queryset.prefetch_related(
                Prefetch('children', queryset=children_queryset, to_attr='prefetched_children')
            )
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'retrieve', 'partial_update'):
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


@extend_schema_view(
    get=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Получить изображение оргструктуры',
        description=READ_ROLES,
        responses={200: OrgStructureImageSerializer, 404: None},
    ),
    post=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Загрузить изображение оргструктуры',
        description=WRITE_ROLES,
        request={'multipart/form-data': OrgStructureImageUploadSerializer},
        responses={201: OrgStructureImageSerializer},
    ),
    patch=extend_schema(
        tags=[STRUCTURE_TAG],
        summary='Обновить изображение оргструктуры',
        description=WRITE_ROLES,
        request={'multipart/form-data': OrgStructureImageUploadSerializer},
        responses={200: OrgStructureImageSerializer},
    ),
)
class OrgStructureImageView(APIView):
    """Singleton-ресурс изображения организационной структуры."""

    parser_classes = (MultiPartParser,)

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsHR()]

    def get(self, request):
        instance = OrgStructureImage.objects.first()
        if instance is None:
            return Response({'detail': 'Изображение не найдено.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrgStructureImageSerializer(instance, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = OrgStructureImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = OrgStructureImage(image=serializer.validated_data['image'])
        instance.save()
        return Response(
            OrgStructureImageSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):
        serializer = OrgStructureImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = OrgStructureImage(image=serializer.validated_data['image'])
        instance.save()
        return Response(OrgStructureImageSerializer(instance, context={'request': request}).data)


@extend_schema(
    tags=[STRUCTURE_TAG],
    summary='Дерево организационной структуры',
    description=READ_ROLES,
)
class OrgStructureTreeView(APIView):
    """Полное дерево организации, начиная с направлений верхнего уровня."""

    def get(self, request, *args, **kwargs):
        departments = list(get_department_queryset().order_by('display_order', 'name'))
        children_map: dict[int | None, list[Department]] = defaultdict(list)

        for department in departments:
            children_map[department.parent_id].append(department)

        for department in departments:
            department.prefetched_children = children_map.get(department.id, [])

        roots = children_map.get(None, [])

        serializer = OrgTreeNodeSerializer(roots, many=True)
        return Response(serializer.data)
