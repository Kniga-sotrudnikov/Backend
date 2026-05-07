from rest_framework import serializers

from .models import Department


class DepartmentBriefSerializer(serializers.ModelSerializer):
    """Краткая информация о подразделении для списков."""

    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'type',
            'display_order',
        )


class DepartmentDetailSerializer(serializers.ModelSerializer):
    """Детальная информация о подразделении с вложенными дочерними элементами."""

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
            'children',
        )


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
        # Если данные были предзагружены, берем их из атрибута, чтобы не было запроса в БД
        children = getattr(obj, 'prefetched_children', obj.children.active())
        if children:
            return OrgTreeNodeSerializer(children, many=True).data
        return tuple()
