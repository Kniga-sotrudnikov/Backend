from django.urls import path
from notifications.views import BirthdaySettingsAPIView

urlpatterns = [
    path('admin/birthdays/settings/', BirthdaySettingsAPIView.as_view(), name='birthday-settings'),
]
