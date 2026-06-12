from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHR
from core.pagination import StandardPagination
from employees.models import Employee
from employees.serializers import EmployeeBriefSerializer
from favorites.models import Favorite
from favorites.serializers import FavoriteAddSerializers, FavoriteResponseSerializers


class FavoritesAPIViews(APIView):
    """Пользовательские эндпоинты избранного список, добавление, удаление."""

    pagination_class = StandardPagination

    def get(self, request):
        """Пагинированный список сотрудников текущего пользователя, код статус 200."""
        favorite_employee_ids = Favorite.objects.filter(user=request.user).values_list('employee_id', flat=True)
        queryset = (
            Employee.objects.filter(id__in=favorite_employee_ids)
            .select_related('department', 'department__parent')
            .prefetch_related('employee_tags__tag')
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset=queryset, request=request)
        serializer = EmployeeBriefSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Добавить сотрудника в избранное, код-статус 201."""
        serializer = FavoriteAddSerializers(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save()
        response_serializers = FavoriteResponseSerializers(favorite)
        return Response(response_serializers.data, status=status.HTTP_201_CREATED)

    def delete(self, request, employee_id):
        """Удалить сотрудника из избранного текущего пользователя, код-статус 204."""
        favorite = get_object_or_404(Favorite, user=request.user, employee_id=employee_id)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminFavoritesAPIViews(APIView):
    permission_classes = [IsHR]

    def get(self, request): ...

    def post(self, request): ...

    def delete(self, request, employee_id): ...
