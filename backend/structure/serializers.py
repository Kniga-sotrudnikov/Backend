from rest_framework import serializers

from .models import Department


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
    children = serializers.SerializerMethodField()

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

    def get_children(self, obj):
        children = getattr(obj, 'prefetched_children', None)
        if children is None:
            children = obj.children.all()
        return DepartmentBriefSerializer(children, many=True).data


class OrgTreeNodeSerializer(serializers.ModelSerializer):
    """Сериализатор для рекурсивного отображения дерева организации."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'type',
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
