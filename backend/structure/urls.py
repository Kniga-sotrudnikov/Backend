from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, DirectionListView, OrgStructureTreeView

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')

urlpatterns = [
    # Список направлений верхнего уровня
    path('directions/', DirectionListView.as_view(), name='direction-list'),
    # Эндпоинт для получения дерева организации
    path('org-structure/tree/', OrgStructureTreeView.as_view(), name='org-structure-tree'),
    # Базовые CRUD операции для /departments/ и /departments/{id}/
    path('', include(router.urls)),
]
