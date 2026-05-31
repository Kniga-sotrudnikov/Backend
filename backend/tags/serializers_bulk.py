from rest_framework import serializers
from employees.models import Employee
from tags.models import Tag


class BulkTagsSerializer(serializers.Serializer):
    employee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=50
    )

    def validate_employee_ids(self, value):
        existing_ids = set(
            Employee.objects.filter(id__in=value)
            .values_list('id', flat=True)
        )
        missing_ids = set(value) - existing_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Сотрудники не найдены: {list(missing_ids)}"
            )
        return value

    def validate_tag_ids(self, value):
        existing_ids = set(
            Tag.objects.filter(id__in=value)
            .values_list('id', flat=True)
        )
        missing_ids = set(value) - existing_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Теги не найдены: {list(missing_ids)}"
            )
        return value


class BulkAddTagsSerializer(BulkTagsSerializer):
    pass


class BulkRemoveTagsSerializer(BulkTagsSerializer):
    pass
