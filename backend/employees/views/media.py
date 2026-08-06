from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, status
from rest_framework.generics import UpdateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsHR
from employees.models import Employee
from employees.serializers import EmployeePhotoUploadSerializer

photo_upload_response_serializer = inline_serializer(
    name='EmployeePhotoUploadResponse',
    fields={'photo_url': serializers.URLField()},
)


@extend_schema_view(
    post=extend_schema(
        summary='Загрузить фотографию сотрудника',
        description='Доступно только HR. Загружает фото и генерирует миниатюру.',
        request={'multipart/form-data': EmployeePhotoUploadSerializer},
        responses={status.HTTP_200_OK: photo_upload_response_serializer},
    ),
    patch=extend_schema(
        summary='Заменить фотографию сотрудника',
        description='Доступно только HR. Старые файлы оригинала и миниатюры удаляются из хранилища.',
        request={'multipart/form-data': EmployeePhotoUploadSerializer},
        responses={status.HTTP_200_OK: photo_upload_response_serializer},
    ),
    delete=extend_schema(
        summary='Удалить фотографию сотрудника',
        description=(
            'Доступно только HR. Удаляет оригинал и миниатюру из хранилища, очищает поля photo и photo_thumb. '
            'После удаления photo_url и photo_original_url в карточке сотрудника возвращаются как null.'
        ),
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Фотография удалена')},
    ),
)
class EmployeePhotoUploadView(UpdateAPIView):
    """Эндпоинт загрузки и обновления фотографии сотрудника."""

    queryset = Employee.all_objects.all()
    serializer_class = EmployeePhotoUploadSerializer
    parser_classes = (MultiPartParser,)
    permission_classes = (IsHR,)
    lookup_field = 'id'
    http_method_names = ['post', 'patch', 'delete', 'head', 'options']

    def post(self, request, *args, **kwargs):
        return self._upload_photo(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self._upload_photo(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.photo:
            instance.photo.delete(save=False)
        if instance.photo_thumb:
            instance.photo_thumb.delete(save=False)
        instance.photo = None
        instance.photo_thumb = None
        instance.save(update_fields=['photo', 'photo_thumb'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _upload_photo(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(
            {'photo_url': request.build_absolute_uri(updated_instance.photo.url)}, status=status.HTTP_200_OK
        )
