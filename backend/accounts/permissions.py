from rest_framework.permissions import SAFE_METHODS, BasePermission


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
        if request.user.is_hr:
            return True
        if request.method in SAFE_METHODS:
            return obj.user.id == request.user.id
        return False
