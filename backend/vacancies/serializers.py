from rest_framework import serializers
from vacancies.models import Vacancy

from structure.serializers import DepartmentDetailSerializer


class VacancyBriefSerializer(serializers.ModelSerializer):
    """Сериализатор для списка вакансий."""

    department_name = serializers.CharField(
        source='department.name',
        read_only=True,
    )

    class Meta:
        model = Vacancy
        fields = (
            'id',
            'title',
            'department_name',
            'status',
            'created_at',
        )


class VacancyDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор вакансий со всеми полями."""

    department = DepartmentDetailSerializer(read_only=True)

    class Meta:
        model = Vacancy
        fields = (
            'id',
            'title',
            'department',
            'description',
            'status',
            'created_at',
            'updated_at',
        )


class VacancyAdminSerializer(serializers.ModelSerializer):
    """Сериализатор вакансий для admin enpoints."""

    class Meta:
        model = Vacancy
        fields = (
            'id',
            'title',
            'department',
            'description',
            'status',
        )
