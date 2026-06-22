from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR
from core.constants import FAVORITES_TAG, READ_ROLES, WRITE_ROLES
from employees.serializers import EmployeeBriefSerializer
from employees.views.employee import get_employee_queryset
from favorites.favorite_paginate import paginate_queryset
from favorites.models import Favorite
from favorites.serializers import (
    FavoriteAddAdmin,
    FavoriteAddSerializers,
    FavoriteAdminResponseSerializer,
    FavoriteAdminSerializer,
    FavoriteResponseSerializers,
)


class FavoritesAPIViews(APIView):
    """Пользовательские эндпоинты избранного список, добавление, удаление."""

    @extend_schema(
        tags=[FAVORITES_TAG],
        summary='Список избранных сотрудников',
        description=READ_ROLES,
    )
    def get(self, request):
        """Пагинированный список сотрудников текущего пользователя, код-статус 200."""
        queryset = get_employee_queryset().filter(favorited_by__user=request.user).distinct()
        page, paginator = paginate_queryset(queryset, request)
        serializer = EmployeeBriefSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=[FAVORITES_TAG],
        summary='Добавить сотрудника в избранное',
        description=READ_ROLES,
        request=FavoriteAddSerializers,
    )
    def post(self, request):
        """Добавить сотрудника в избранное, код-статус 201."""
        serializer = FavoriteAddSerializers(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save()
        response_serializers = FavoriteResponseSerializers(favorite)
        return Response(response_serializers.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=[FAVORITES_TAG],
        summary='Удалить сотрудника из избранного',
        description=READ_ROLES,
    )
    def delete(self, request, employee_id):
        """Удалить сотрудника из избранного текущего пользователя, код-статус 204."""
        favorite = get_object_or_404(Favorite, user=request.user, employee_id=employee_id)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminFavoritesAPIViews(APIView):
    permission_classes = [IsHR]

    @extend_schema(
        tags=[FAVORITES_TAG],
        summary='Список всех записей избранного',
        description=WRITE_ROLES,
    )
    def get(self, request):
        """Пагинированный список всех записей избранного, код-статус 200."""
        queryset = Favorite.objects.all().select_related('user', 'employee', 'employee__department')
        page, paginator = paginate_queryset(queryset, request)
        serializer = FavoriteAdminSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=[FAVORITES_TAG],
        summary='Добавить сотрудника в избранное с заметкой',
        description=WRITE_ROLES,
        request=FavoriteAddAdmin,
    )
    def post(self, request):
        """Добавить сотрудника в избранное с заметкой, код-статус 201."""
        serializer = FavoriteAddAdmin(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save()
        response_serializer = FavoriteAdminResponseSerializer(favorite)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=[FAVORITES_TAG],
        summary='Удалить запись из избранного',
        description=WRITE_ROLES,
    )
    def delete(self, request, employee_id):
        """Удалить запись из избранного текущего HR, код-статус 204."""
        favorite = get_object_or_404(Favorite, user=request.user, employee_id=employee_id)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
