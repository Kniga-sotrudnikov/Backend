from medias.validators import validate_file_size, validate_org_image_extension
from rest_framework import serializers

from .models import Department, OrgStructureImage


class DepartmentBriefSerializer(serializers.ModelSerializer):
    """Краткая информация о подразделении для списков."""

    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'type',
            'display_order',
            'employee_count',
        )


class DepartmentDetailSerializer(serializers.ModelSerializer):
    """Детальная информация о подразделении с вложенными дочерними элементами."""

    employee_count = serializers.IntegerField(read_only=True)
    children = DepartmentBriefSerializer(many=True, read_only=True)

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'short_name',
            'description',
            'type',
            'parent',
            'display_order',
            'is_active',
            'employee_count',
            'children',
        )


class OrgTreeNodeSerializer(serializers.ModelSerializer):
    """Сериализатор для рекурсивного отображения дерева организации."""

    employee_count = serializers.IntegerField(read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'type',
            'employee_count',
            'children',
        )

    def get_children(self, obj):
        """Использует предзагруженные данные из prefetch_related."""
        # Если данные были предзагружены, берем их из атрибута, чтобы не было запроса в БД
        children = getattr(obj, 'prefetched_children', obj.children.all())
        if children:
            return OrgTreeNodeSerializer(children, many=True).data
        return tuple()


class OrgStructureImageSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения изображения оргструктуры."""

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = OrgStructureImage
        fields = ('image_url', 'updated_at')

    def get_image_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url)


class OrgStructureImageUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки изображения оргструктуры."""

    image = serializers.ImageField(
        validators=[validate_org_image_extension, validate_file_size],
        help_text='Изображение оргструктуры (JPEG, PNG до 5MB)',
    )
