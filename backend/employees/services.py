from dataclasses import dataclass
from datetime import date

from django.contrib.auth.base_user import AbstractBaseUser
from employees.models import Employee, Status
from structure.models import Department


@dataclass
class EmployeeCreate:
    full_name: str
    job_title: str
    email: str
    birthday: date
    department: Department
    user: AbstractBaseUser | None = None
    role_description: str = ''
    phone: str = ''
    interests: str = ''


@dataclass
class EmployeeUpdate:
    full_name: str | None = None
    job_title: str | None = None
    email: str | None = None
    birthday: date | None = None
    department: Department | None = None
    user: AbstractBaseUser | None = None
    role_description: str | None = None
    phone: str | None = None
    interests: str | None = None


def create_employee(data: EmployeeCreate, created_by: AbstractBaseUser | None = None) -> Employee:
    """
    Создаёт сотрудника.

    Args:
        data: Данные нового сотрудника.
        created_by: Пользователь, создавший карточку.

    Returns:
        Созданный объект Employee.
    """
    return Employee.objects.create(**data.__dict__, created_by=created_by)


def update_employee(employee: Employee, data: EmployeeUpdate, updated_by: AbstractBaseUser | None = None) -> Employee:
    """
    Обновляет данные сотрудника.

    Args:
        employee: Обновляемый сотрудник.
        data: Объект с обновляемыми данными сотрудника.
        updated_by: Пользователь, выполнивший обновление.

    Returns:
        Обновлённый объект сотрудника.
    """
    for field, value in data.__dict__.items():
        if value is not None:
            setattr(employee, field, value)
    if updated_by is not None:
        employee.updated_by = updated_by
    employee.save()
    return employee


def archive_employee(
    employee: Employee,
    updated_by: AbstractBaseUser | None = None,
) -> Employee:
    """
    Архивирует сотрудника через soft delete.

    Args:
        employee: Сотрудник для архивирования.
        updated_by: Пользователь, выполнивший архивирование.

    Returns:
        Архивированный сотрудник.
    """
    employee.status = Status.ARCHIVED
    update_fields = ['status']
    if updated_by is not None:
        employee.updated_by = updated_by
        update_fields.append('updated_by')
    employee.save(update_fields=update_fields)
    employee.delete()
    return employee
