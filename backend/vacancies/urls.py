from django.urls import include, path
from rest_framework.routers import DefaultRouter
from vacancies.views import VacancyAdminViewSet, VacancyViewSet

router = DefaultRouter()

router.register(
    'vacancies',
    VacancyViewSet,
    basename='vacancy',
)

router.register(
    'admin/vacancies',
    VacancyAdminViewSet,
    basename='admin-vacancy',
)

urlpatterns = [
    path('', include(router.urls)),
]
