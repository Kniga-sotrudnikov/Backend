from django.urls import include, path
from employees.views import EmployeeAdminViewSet, EmployeePhotoUploadView, EmployeeViewSet, EmployeePDFExportView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')
router.register('admin/employees', EmployeeAdminViewSet, basename='admin-employee')

urlpatterns = [
    path('admin/employees/<int:id>/photo/', EmployeePhotoUploadView.as_view(), name='employee-photo-upload'),
    path('', include(router.urls)),
    path('employees/<int:id>/export/pdf/', EmployeePDFExportView.as_view(), name='employee-pdf-export'),
]
