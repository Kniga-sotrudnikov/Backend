from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR
from core.constants import READ_ROLES, TAGS_TAG, WRITE_ROLES
from tags.models import Tag
from tags.serializers import TagSerializer
from tags.serializers_bulk import BulkAddTagsSerializer, BulkRemoveTagsSerializer
from tags.services import bulk_assign_tags, bulk_remove_tags


@extend_schema_view(
    list=extend_schema(
        tags=[TAGS_TAG],
        summary='Список тегов',
        description=READ_ROLES,
    ),
    create=extend_schema(
        tags=[TAGS_TAG],
        summary='Создание тега',
        description=WRITE_ROLES,
    ),
    retrieve=extend_schema(
        tags=[TAGS_TAG],
        summary='Подробности тега',
        description=READ_ROLES,
    ),
    partial_update=extend_schema(
        tags=[TAGS_TAG],
        summary='Частичное обновление тега',
        description=WRITE_ROLES,
    ),
    destroy=extend_schema(
        tags=[TAGS_TAG],
        summary='Удаление тега',
        description=WRITE_ROLES,
    ),
)
class TagViewSet(viewsets.ModelViewSet):
    """API endpoint для просмотра и редактирования тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action in ('create', 'partial_update', 'destroy'):
            return [IsHR()]
        return super().get_permissions()


class BulkAddTagsView(APIView):
    permission_classes = [IsHR]

    @extend_schema(
        tags=[TAGS_TAG],
        summary='Массовое добавление тегов',
        request=BulkAddTagsSerializer,
        responses={200: None, 400: None},
    )
    def post(self, request):
        serializer = BulkAddTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bulk_assign_tags(
            employee_ids=serializer.validated_data['employee_ids'],
            tag_ids=serializer.validated_data['tag_ids'],
            by_user=request.user,
        )

        return Response(status=status.HTTP_200_OK)


class BulkRemoveTagsView(APIView):
    permission_classes = [IsHR]

    @extend_schema(
        tags=[TAGS_TAG],
        summary='Массовое удаление тегов',
        request=BulkRemoveTagsSerializer,
        responses={200: None, 400: None},
    )
    def post(self, request):
        serializer = BulkRemoveTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bulk_remove_tags(
            employee_ids=serializer.validated_data['employee_ids'],
            tag_ids=serializer.validated_data['tag_ids'],
            by_user=request.user,
        )

        return Response(status=status.HTTP_200_OK)
