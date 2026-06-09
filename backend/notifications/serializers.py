from notifications.models import BirthdayNotificationSettings
from rest_framework import serializers


class BirthdayNotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirthdayNotificationSettings
        fields = ['email_enabled', 'days_before', 'recipients']
