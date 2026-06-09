from django.urls import include, path
from employees.views import (AdminUpcomingBirthdaysAPIView,
                             EmployeeAdminViewSet, EmployeeBirthdaysAPIView,
                             EmployeePDFExportView, EmployeePhotoUploadView,
                             EmployeeViewSet)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')
router.register('admin/employees', EmployeeAdminViewSet, basename='admin-employee')

urlpatterns = [
    path('admin/employees/<int:id>/photo/', EmployeePhotoUploadView.as_view(), name='employee-photo-upload'),
    path(
        'admin/birthdays/upcoming/',
        AdminUpcomingBirthdaysAPIView.as_view(),
        name='admin-upcoming-birthdays',
    ),
    path(
        'employees/birthdays/',
        EmployeeBirthdaysAPIView.as_view(),
        name='employee-birthdays',
    ),
    path(
        'employees/<int:id>/export/pdf/',
        EmployeePDFExportView.as_view(),
        name='employee-pdf-export',
    ),
    path('', include(router.urls)),
]
