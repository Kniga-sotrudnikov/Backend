from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, DirectionListView, OrgStructureImageView, OrgStructureTreeView

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('directions/', DirectionListView.as_view(), name='direction-list'),
    path('org-structure/image/', OrgStructureImageView.as_view(), name='org-structure-image'),
    path('org-structure/tree/', OrgStructureTreeView.as_view(), name='org-structure-tree'),
    path('', include(router.urls)),
]
