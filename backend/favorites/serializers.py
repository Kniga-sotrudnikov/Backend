from rest_framework import serializers

from employees.models import Employee
from favorites.models import Favorite


class FavoriteAddSerializers(serializers.Serializer):
    """Сериализатор добавления в избранное с валидацией существования и уникальности сотрудника."""

    employee_id = serializers.IntegerField()

    def validate_employee_id(self, value):
        if not Employee.objects.filter(id=value).exists():
            raise serializers.ValidationError('Сотрудник не найден.')
        return value

    def validate(self, data):
        if Favorite.objects.filter(user=self.context.get('request').user, employee_id=data.get('employee_id')).exists():
            raise serializers.ValidationError('сотрудник уже в избранном')
        return data

    def create(self, validated_data):
        add_favorite = Favorite.objects.create(
            user=self.context.get('request').user, employee_id=validated_data.get('employee_id')
        )
        return add_favorite


class FavoriteResponseSerializers(serializers.ModelSerializer):
    """Сериализатор для api-ответа."""

    class Meta:
        model = Favorite
        fields = ('employee_id', 'created_at')
