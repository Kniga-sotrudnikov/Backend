from notifications.models import BirthdayNotificationSettings
from notifications.serializers import BirthdayNotificationSettingsSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR


class BirthdaySettingsAPIView(APIView):
    permission_classes = [IsHR]

    def get(self, request):
        settings = BirthdayNotificationSettings.load()
        serializer = BirthdayNotificationSettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        settings = BirthdayNotificationSettings.load()
        serializer = BirthdayNotificationSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
