from employees.models import Employee
from medias.validators import validate_file_extension, validate_file_size
from rest_framework import serializers


class EmployeePhotoUploadSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(
        validators=(
            validate_file_extension,
            validate_file_size,
        ),
        required=True,
    )

    class Meta:
        model = Employee
        fields = ('photo',)

    #     def update(self, instance, validated_data):
    #         instance.photo = validated_data['photo']
    #         instance.save()
    #         return instance

    def update(self, instance, validated_data):
        # Если у сотрудника уже были файлы, физически удаляем их с диска перед заменой
        if instance.photo:
            instance.photo.delete(save=False)
        if instance.photo_thumb:
            instance.photo_thumb.delete(save=False)

        # Присваиваем новое фото и сохраняем инстанс
        instance.photo = validated_data['photo']
        instance.save()
        return instance
