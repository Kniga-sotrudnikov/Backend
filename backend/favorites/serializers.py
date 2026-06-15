from django.shortcuts import get_object_or_404
from rest_framework import serializers

from employees.models import Employee
from favorites.models import Favorite


class BaseFavoriteSerializer(serializers.ModelSerializer):
    """Базовый сериализатор избранного: 404 если сотрудник не найден, 400 если уже в избранном."""

    employee_id = serializers.IntegerField()

    class Meta:
        model = Favorite
        fields = ('employee_id',)

    def validate(self, data):
        employee = get_object_or_404(Employee, pk=data.pop('employee_id'))
        if Favorite.objects.filter(user=self.context['request'].user, employee=employee).exists():
            raise serializers.ValidationError('Сотрудник уже в избранном')
        data['employee'] = employee
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return Favorite.objects.create(**validated_data)


class FavoriteAddSerializers(BaseFavoriteSerializer):
    """Сериализатор добавления в избранное с валидацией существования и уникальности сотрудника."""

    pass


class FavoriteResponseSerializers(serializers.ModelSerializer):
    """Сериализатор для api-ответа."""

    class Meta:
        model = Favorite
        fields = ('employee_id', 'created_at')


class FavoriteAdminSerializer(serializers.ModelSerializer):
    """Получения списка избранного для HR."""

    class Meta:
        model = Favorite
        fields = (
            'id',
            'user',
            'employee',
            'note',
            'created_at',
        )


class FavoriteAddAdmin(BaseFavoriteSerializer):
    """Сериализатор для HR: добавления в избранное с заметкой."""

    class Meta(BaseFavoriteSerializer.Meta):
        fields = BaseFavoriteSerializer.Meta.fields + ('note',)


class FavoriteAdminResponseSerializer(serializers.ModelSerializer):
    """Сериализатор ответа AF2: employee_id + note + created_at."""

    class Meta:
        model = Favorite
        fields = ('employee_id', 'note', 'created_at')
