from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from core.constants import READ_ROLES, TAGS_TAG, WRITE_ROLES
from tags.models import Tag
from tags.serializers import TagSerializer


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
        description=WRITE_ROLES,
    ),
    update=extend_schema(
        tags=[TAGS_TAG],
        summary='Полное обновление тега',
        description=WRITE_ROLES,
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
