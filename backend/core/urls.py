from django.urls import path

from core.views import AdminSummaryView

urlpatterns = [
    path('admin/summary/', AdminSummaryView.as_view(), name='admin-summary'),
]
