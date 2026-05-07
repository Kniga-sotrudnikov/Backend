from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Tag
from .serializers import TagSerializer


class TagViewSet(viewsets.ModelViewSet):
    """API endpoint для просмотра и редактирования тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
