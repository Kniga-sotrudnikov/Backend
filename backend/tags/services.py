from django.utils import timezone
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from .models import EmployeeTag, Tag
from employees.models import Employee
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
        raise ValueError(f"Идентификаторы тегов не найдены: {missing_tag_ids}")

    assigned_tag_ids = set(
        EmployeeTag.objects.filter(employee=employee, is_deleted=False).values_list('tag_id', flat=True)
    )

    tags_to_assign = [
        EmployeeTag(employee=employee, tag_id=tag_id, assigned_by=by_user)
        for tag_id in tag_ids
        if tag_id not in assigned_tag_ids
    ]

    if tags_to_assign:
        EmployeeTag.objects.bulk_create(tags_to_assign)


def remove_tags(employee: Employee, tag_ids: list[int], by_user: User) -> None:
    """
    Мягко снимает теги с сотрудника, сохраняя аудит.
    """
    validate_employee_tag_assignment(employee, tag_ids, by_user)

    tags_to_soft_delete = EmployeeTag.objects.filter(
        employee=employee,
        tag_id__in=tag_ids,
        is_deleted=False
    )

    if tags_to_soft_delete.exists():
        with transaction.atomic():
            tags_to_soft_delete.update(
                is_deleted=True,
                removed_by=by_user,
                removed_at=timezone.now()
            )
