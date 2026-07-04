from medias.validators import validate_file_size, validate_org_image_extension
from rest_framework import serializers

from employees.models import Employee

from .models import Department, OrgStructureImage


class DepartmentHeadSerializer(serializers.ModelSerializer):
    """Краткая информация о руководителе подразделения."""

    class Meta:
        model = Employee
        fields = (
            'id',
            'full_name',
            'job_title',
        )


class DepartmentBriefSerializer(serializers.ModelSerializer):
    """Краткая информация о подразделении для списков."""

    employee_count = serializers.IntegerField(read_only=True)
    head = DepartmentHeadSerializer(read_only=True)
    head_id = serializers.PrimaryKeyRelatedField(
        source='head',
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'type',
            'head',
            'head_id',
            'display_order',
            'employee_count',
        )


class DepartmentDetailSerializer(serializers.ModelSerializer):
    """Детальная информация о подразделении с вложенными дочерними элементами."""

    employee_count = serializers.IntegerField(read_only=True)
    children = serializers.SerializerMethodField()
    head = DepartmentHeadSerializer(read_only=True)
    head_id = serializers.PrimaryKeyRelatedField(
        source='head',
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'short_name',
            'description',
            'type',
            'parent',
            'head',
            'head_id',
            'display_order',
            'is_active',
            'employee_count',
            'children',
        )

    def get_children(self, obj):
        children = getattr(obj, 'prefetched_children', None)
        if children is None:
            children = obj.children.all()
        return DepartmentBriefSerializer(children, many=True).data


class OrgTreeNodeSerializer(serializers.ModelSerializer):
    """Сериализатор для рекурсивного отображения дерева организации."""

    employee_count = serializers.IntegerField(read_only=True)
    children = serializers.SerializerMethodField()
    head = DepartmentHeadSerializer(read_only=True)
    head_id = serializers.PrimaryKeyRelatedField(
        source='head',
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'type',
            'head',
            'head_id',
            'employee_count',
            'children',
        )

    def get_children(self, obj):
        """Использует предзагруженные данные из prefetch_related."""
        children = getattr(obj, 'prefetched_children', None)
        if children is None:
            children = obj.children.all()
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
