from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from employees.models import Employee

from .models import EmployeeTag, Tag
from .validators import validate_employee_tag_assignment

User = get_user_model()


@transaction.atomic
def assign_tags(employee: Employee, tag_ids: list[int], by_user: User) -> None:
    """
    Назначает список тегов сотруднику.

    Атомарно и идемпотентно.
    """
    validate_employee_tag_assignment(employee, tag_ids, by_user)

    existing_tag_ids = set(Tag.objects.filter(id__in=tag_ids).values_list('id', flat=True))
    if len(existing_tag_ids) != len(tag_ids):
        missing_tag_ids = set(tag_ids) - existing_tag_ids
        raise ValueError(f'Идентификаторы тегов не найдены: {missing_tag_ids}')

    for tag_id in tag_ids:
        employee_tag, created = EmployeeTag.all_objects.update_or_create(
            employee=employee,
            tag_id=tag_id,
            defaults={
                'is_deleted': False,
                'deleted_at': None,
                'removed_by': None,
                'removed_at': None,
                'assigned_by': by_user,
                'assigned_at': timezone.now(),
            },
        )


def remove_tags(employee: Employee, tag_ids: list[int], by_user: User) -> None:
    """Мягко снимает теги с сотрудника, сохраняя аудит."""
    validate_employee_tag_assignment(employee, tag_ids, by_user)

    tags_to_soft_delete = EmployeeTag.objects.filter(employee=employee, tag_id__in=tag_ids, is_deleted=False)

    if tags_to_soft_delete.exists():
        with transaction.atomic():
            tags_to_soft_delete.update(is_deleted=True, removed_by=by_user, removed_at=timezone.now())


@transaction.atomic
def bulk_assign_tags(employee_ids: list[int], tag_ids: list[int], by_user: User) -> None:
    """
    Массовое назначение тегов нескольким сотрудникам.

    Если хотя бы одна операция не удалась - откатывает всё.
    """
    employees = Employee.objects.filter(id__in=employee_ids)

    for employee in employees:
        assign_tags(employee, tag_ids, by_user)


@transaction.atomic
def bulk_remove_tags(employee_ids: list[int], tag_ids: list[int], by_user: User) -> None:
    """
    Массовое снятие тегов с нескольких сотрудников.

    Если хотя бы одна операция не удалась - откатывает всё.
    """
    employees = Employee.objects.filter(id__in=employee_ids)

    for employee in employees:
        remove_tags(employee, tag_ids, by_user)
