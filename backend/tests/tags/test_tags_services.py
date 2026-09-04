from tags.models import EmployeeTag
from tags.services import assign_tags, bulk_assign_tags, bulk_remove_tags, remove_tags


def test_assign_tags_with_audit(db, employee_instance, tag, hr):
    """Проверка успешного назначения тега сотруднику и логирования аудита."""
    assert not EmployeeTag.objects.filter(employee=employee_instance, tag=tag).exists()

    assign_tags(employee=employee_instance, tag_ids=[tag.id], by_user=hr)

    # Проверяем, что связь создалась
    emp_tag = EmployeeTag.objects.get(employee=employee_instance, tag=tag)
    assert emp_tag.is_deleted is False
    # Проверяем аудит создания
    assert emp_tag.assigned_by == hr
    assert emp_tag.assigned_at is not None


def test_assign_tags_reassign_idempotency(db, employee_instance, tag, hr):
    """Проверка идемпотентности: повторное назначение тега обновляет запись, а не дублирует её."""
    # Назначаем первый раз
    assign_tags(employee=employee_instance, tag_ids=[tag.id], by_user=hr)
    first_count = EmployeeTag.all_objects.filter(employee=employee_instance, tag=tag).count()
    assert first_count == 1

    # Назначаем второй раз (перепривязка)
    assign_tags(employee=employee_instance, tag_ids=[tag.id], by_user=hr)
    second_count = EmployeeTag.all_objects.filter(employee=employee_instance, tag=tag).count()
    # Записей в БД всё ещё должно быть ровно одна
    assert second_count == 1


def test_remove_tags_with_audit(db, employee_instance, tag, hr, user):
    """Проверка мягкого удаления тега с сотрудника и сохранения аудита удаления."""
    # Сначала привязываем тег силами HR
    assign_tags(employee=employee_instance, tag_ids=[tag.id], by_user=hr)

    # Теперь снимаем тег силами другого пользователя (например, обычного юзера)
    remove_tags(employee=employee_instance, tag_ids=[tag.id], by_user=user)

    # Тег должен исчезнуть из активных
    assert not EmployeeTag.objects.filter(employee=employee_instance, tag=tag).exists()

    # Но запись должна остаться в all_objects в состоянии мягкого удаления
    deleted_tag = EmployeeTag.all_objects.get(employee=employee_instance, tag=tag)
    assert deleted_tag.is_deleted is True
    # Проверяем аудит удаления
    assert deleted_tag.removed_by == user
    assert deleted_tag.removed_at is not None


def test_bulk_assign_and_remove_tags(db, three_employees, tag, hr):
    """Проверка массового назначения и массового снятия тегов для списка сотрудников."""
    employee_ids = [emp.id for emp in three_employees]

    # 1. Массово назначаем тег
    bulk_assign_tags(employee_ids=employee_ids, tag_ids=[tag.id], by_user=hr)

    # Проверяем, что у каждого сотрудника появился этот тег
    for emp in three_employees:
        assert EmployeeTag.objects.filter(employee=emp, tag=tag).exists()

    # 2. Массово снимаем тег
    bulk_remove_tags(employee_ids=employee_ids, tag_ids=[tag.id], by_user=hr)

    # Проверяем, что у всех сотрудников тег мягко удалился
    for emp in three_employees:
        assert not EmployeeTag.objects.filter(employee=emp, tag=tag).exists()
        assert EmployeeTag.all_objects.filter(employee=emp, tag=tag, is_deleted=True).exists()
