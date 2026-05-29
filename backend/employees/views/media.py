from employees.models import Employee
from employees.serializers import EmployeePhotoUploadSerializer
from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsHR


class EmployeePhotoUploadView(UpdateAPIView):
    """Эндпоинт загрузки и обновления фотографии сотрудника."""

    queryset = Employee.all_objects.all()
    serializer_class = EmployeePhotoUploadSerializer
    parser_classes = (MultiPartParser,)
    permission_classes = (IsHR,)
    lookup_field = 'id'

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(
            {'photo_url': request.build_absolute_uri(updated_instance.photo.url)}, status=status.HTTP_200_OK
        )
