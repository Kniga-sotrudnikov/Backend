from rest_framework.permissions import BasePermission


class IsHR(BasePermission):
    """Доступ для Эйчар."""

    def has_permission(self, request, view):
        """Доступ только эйчар."""
        return request.user.is_hr


class IsEmployee(BasePermission):
    """Доступ для Cотрудника."""

    def has_permission(self, request, view):
        """Доступ только сотруднику."""
        return request.user.is_employee


class IsOwnerOrHR(BasePermission):
    """Доступ для Эйчар или владельца объекта."""

    def has_permission(self, request, view):
        """Пропускаем, так как пользователи по дефолту авторизированны (DEFAULT_PERMISSION_CLASSES)."""
        return True

    def has_object_permission(self, request, view, obj):
        """Проверка на уровне объекта эйчар или сотрудник."""
        return request.user.is_hr or obj.user.id == request.user.id
