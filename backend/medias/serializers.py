from rest_framework import serializers

from backend.medias.validators import validate_file_extension, validate_file_size


class EmployeePhotoUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки фотографий сотрудников."""

    photo = serializers.ImageField(
        validators=[validate_file_extension, validate_file_size],
        help_text='Загрузите файл изображения (JPEG, PNG, WebP до 5MB)',
    )
