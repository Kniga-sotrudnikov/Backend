from django.urls import include, path
from employees.views.employee import EmployeeAdminViewSet, EmployeeViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')
router.register('admin/employees', EmployeeAdminViewSet, basename='admin-employee')

urlpatterns = [
    path('', include(router.urls)),
]
