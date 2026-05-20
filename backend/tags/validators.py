from django.contrib.auth import get_user_model
from Employees.models import Employee

User = get_user_model()

def validate_employee_tag_assignment(employee: Employee, tag_ids: list[int], by_user: User) -> None:
    """Проверяет, что переданные объекты имеют правильные типы."""
    if not isinstance(employee, Employee):
        raise TypeError("employee должен быть объектом Employee")
    if not isinstance(by_user, User):
        raise TypeError("by_user должен быть объектом User")
    if not isinstance(tag_ids, list):
        raise TypeError("tag_ids должен быть списком")
