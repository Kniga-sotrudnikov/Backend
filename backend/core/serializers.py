from rest_framework import serializers


class AdminSummarySerializer(serializers.Serializer):
    """Счётчики для шапки административного интерфейса."""

    employees_count = serializers.IntegerField(help_text='Количество активных сотрудников')
    directions_count = serializers.IntegerField(help_text='Количество активных направлений')
    vacancies_count = serializers.IntegerField(help_text='Количество открытых вакансий')
