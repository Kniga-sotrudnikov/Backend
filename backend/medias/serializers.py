from medias.validators import validate_file_extension, validate_file_size
from rest_framework import serializers


class EmployeePhotoUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки фотографий сотрудников."""

    photo = serializers.ImageField(
        validators=[validate_file_extension, validate_file_size],
        help_text='Загрузите файл изображения (JPEG, PNG, WebP до 5MB)',
    )
