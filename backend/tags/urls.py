from django.urls import include, path
from rest_framework.routers import DefaultRouter

from tags.views import BulkAddTagsView, BulkRemoveTagsView, TagViewSet

router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    path('', include(router.urls)),
    path('bulk/add-tags/', BulkAddTagsView.as_view(), name='bulk-add-tags'),
    path('bulk/remove-tags/', BulkRemoveTagsView.as_view(), name='bulk-remove-tags'),
]
