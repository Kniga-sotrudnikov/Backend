import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from employees.models import Employee
from structure.models import Department 
from tags.models import Tag, EmployeeTag
from tags.services import assign_tags, remove_tags, bulk_assign_tags, bulk_remove_tags
from tags.validators import validate_employee_tag_assignment

User = get_user_model()


@pytest.fixture
def department():
    """Создает тестовый департамент"""
    return Department.objects.create(
        name="IT Department",
        type="department"
    )


@pytest.fixture
def user():
    """Создает тестового пользователя"""
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@example.com"
    )


@pytest.fixture
def admin_user():
    """Создает администратора"""
    return User.objects.create_superuser(
        username="admin",
        password="adminpass123",
        email="admin@example.com"
    )


@pytest.fixture
def employee(department):
    """Создает тестового сотрудника"""
    return Employee.objects.create(
        full_name="Тестовый Сотрудник",
        email="test@example.com",
        job_title="Тестировщик",
        birthday="1990-01-01",
        department=department
    )


@pytest.fixture
def another_employee(department):
    """Создает другого тестового сотрудника"""
    return Employee.objects.create(
        full_name="Другой Сотрудник",
        email="another@example.com",
        job_title="Разработчик",
        birthday="1995-05-15",
        department=department
    )


@pytest.fixture
def tags():
    """Создает тестовые теги"""
    return {
        'python': Tag.objects.create(name="Python"),
        'django': Tag.objects.create(name="Django"),
        'postgres': Tag.objects.create(name="PostgreSQL"),
    }


@pytest.mark.django_db
class TestAssignTags:
    """Тесты для функции assign_tags"""

    def test_assign_new_tag_creates_record(self, employee, tags, user):
        """Назначение нового тега → запись в EmployeeTag + assigned_by корректный"""
        tag_ids = [tags['python'].id]

        assign_tags(employee, tag_ids, user)

        employee_tag = EmployeeTag.objects.get(
            employee=employee,
            tag=tags['python']
        )

        assert employee_tag is not None
        assert employee_tag.assigned_by == user
        assert employee_tag.is_deleted is False
        assert employee_tag.assigned_at is not None

    def test_assign_multiple_tags_creates_records(self, employee, tags, user):
        """Назначение нескольких тегов создает несколько записей"""
        tag_ids = [tags['python'].id, tags['django'].id]

        assign_tags(employee, tag_ids, user)

        count = EmployeeTag.objects.filter(employee=employee).count()
        assert count == 2

        employee_tags = EmployeeTag.objects.filter(employee=employee)
        assigned_tag_ids = [et.tag_id for et in employee_tags]
        assert tags['python'].id in assigned_tag_ids
        assert tags['django'].id in assigned_tag_ids

    def test_assign_duplicate_tag_no_duplicate(self, employee, tags, user):
        """Повторное назначение → нет дубликата"""
        tag_ids = [tags['python'].id]

        assign_tags(employee, tag_ids, user)

        assign_tags(employee, tag_ids, user)

        count = EmployeeTag.objects.filter(
            employee=employee,
            tag=tags['python']
        ).count()

        assert count == 1

    def test_assign_tag_to_multiple_employees(self, employee, another_employee, tags, user):
        """Назначение одного тега разным сотрудникам"""
        tag_id = tags['python'].id

        assign_tags(employee, [tag_id], user)
        assign_tags(another_employee, [tag_id], user)

        assert EmployeeTag.objects.filter(employee=employee, tag_id=tag_id).exists()
        assert EmployeeTag.objects.filter(employee=another_employee, tag_id=tag_id).exists()
        assert EmployeeTag.objects.count() == 2

    def test_assign_nonexistent_tag_raises_error(self, employee, user):
        """Назначение несуществующего тега вызывает ошибку"""
        with pytest.raises(ValueError, match="Идентификаторы тегов не найдены"):
            assign_tags(employee, [99999], user)

    def test_assign_empty_tag_list_does_nothing(self, employee, user):
        """Назначение пустого списка тегов ничего не делает"""
        initial_count = EmployeeTag.objects.count()

        assign_tags(employee, [], user)

        assert EmployeeTag.objects.count() == initial_count

    def test_assign_tag_restores_deleted_tag(self, employee, tags, user, admin_user):
        """Назначение ранее удаленного тега восстанавливает его"""
        tag_id = tags['python'].id

        assign_tags(employee, [tag_id], user)

        remove_tags(employee, [tag_id], admin_user)

        deleted_tag = EmployeeTag.all_objects.get(employee=employee, tag_id=tag_id)
        assert deleted_tag.is_deleted is True
        assert deleted_tag.removed_by == admin_user

        assign_tags(employee, [tag_id], user)

        restored_tag = EmployeeTag.all_objects.get(employee=employee, tag_id=tag_id)
        assert restored_tag.is_deleted is False
        assert restored_tag.assigned_by == user
        assert restored_tag.removed_by is None
        assert restored_tag.removed_at is None


@pytest.mark.django_db
class TestRemoveTags:
    """Тесты для функции remove_tags"""

    def test_remove_active_tag_soft_deletes(self, employee, tags, user):
        """Снятие тега → запись помечена удалённой, аудит сохранён"""
        assign_tags(employee, [tags['python'].id], user)

        remove_tags(employee, [tags['python'].id], user)

        employee_tag = EmployeeTag.all_objects.get(
            employee=employee,
            tag=tags['python']
        )

        assert employee_tag.is_deleted is True
        assert employee_tag.removed_by == user
        assert employee_tag.removed_at is not None

    def test_remove_multiple_tags(self, employee, tags, user):
        """Снятие нескольких тегов"""
        assign_tags(employee, [tags['python'].id, tags['django'].id], user)

        remove_tags(employee, [tags['python'].id, tags['django'].id], user)

        python_tag = EmployeeTag.all_objects.get(employee=employee, tag=tags['python'])
        django_tag = EmployeeTag.all_objects.get(employee=employee, tag=tags['django'])

        assert python_tag.is_deleted is True
        assert django_tag.is_deleted is True

    def test_remove_non_existent_tag_does_nothing(self, employee, user):
        """Снятие неназначенного тега ничего не делает"""
        initial_count = EmployeeTag.objects.count()

        remove_tags(employee, [99999], user)

        assert EmployeeTag.objects.count() == initial_count

    def test_remove_already_removed_tag_does_nothing(self, employee, tags, user):
        """Повторное снятие уже удаленного тега ничего не меняет"""
        assign_tags(employee, [tags['python'].id], user)
        remove_tags(employee, [tags['python'].id], user)

        first_removed_at = EmployeeTag.all_objects.get(
            employee=employee, tag=tags['python']
        ).removed_at

        remove_tags(employee, [tags['python'].id], user)

        employee_tag = EmployeeTag.all_objects.get(employee=employee, tag=tags['python'])
        assert employee_tag.removed_at == first_removed_at
        assert employee_tag.is_deleted is True


@pytest.mark.django_db
class TestBulkAssignTags:
    """Тесты для bulk_assign_tags"""

    def test_bulk_assign_to_multiple_employees(self, employee, another_employee, department, tags, user):
        """Bulk добавление тегов 3 сотрудникам"""
        third_employee = Employee.objects.create(
            full_name="Третий Сотрудник",
            email="third@example.com",
            job_title="Дизайнер",
            birthday="1992-03-20",
            department=department

        )

        employee_ids = [employee.id, another_employee.id, third_employee.id]
        tag_ids = [tags['python'].id, tags['django'].id]

        bulk_assign_tags(employee_ids, tag_ids, user)

        for emp_id in employee_ids:
            assert EmployeeTag.objects.filter(
                employee_id=emp_id,
                tag_id=tags['python'].id,
                is_deleted=False
            ).exists()
            assert EmployeeTag.objects.filter(
                employee_id=emp_id,
                tag_id=tags['django'].id,
                is_deleted=False
            ).exists()

        assert EmployeeTag.objects.count() == 6

    def test_bulk_assign_duplicate_tags_no_duplicates(self, employee, another_employee, tags, user):
        """Bulk добавление дублирующихся тегов не создает дубликатов"""
        employee_ids = [employee.id, another_employee.id]
        tag_ids = [tags['python'].id]

        bulk_assign_tags(employee_ids, tag_ids, user)

        bulk_assign_tags(employee_ids, tag_ids, user)

        for emp_id in employee_ids:
            count = EmployeeTag.objects.filter(
                employee_id=emp_id,
                tag_id=tags['python'].id
            ).count()
            assert count == 1

    def test_bulk_assign_partially_existing_tags(self, employee, another_employee, tags, user):
        """Bulk добавление где некоторые теги уже есть"""
        assign_tags(employee, [tags['python'].id], user)

        employee_ids = [employee.id, another_employee.id]
        tag_ids = [tags['python'].id, tags['django'].id]

        bulk_assign_tags(employee_ids, tag_ids, user)

        assert EmployeeTag.objects.filter(
            employee=employee,
            tag=tags['python'],
            is_deleted=False
        ).exists()
        assert EmployeeTag.objects.filter(
            employee=employee,
            tag=tags['django'],
            is_deleted=False
        ).exists()

        assert EmployeeTag.objects.filter(
            employee=another_employee,
            tag=tags['python'],
            is_deleted=False
        ).exists()
        assert EmployeeTag.objects.filter(
            employee=another_employee,
            tag=tags['django'],
            is_deleted=False
        ).exists()


@pytest.mark.django_db
class TestBulkRemoveTags:
    """Тесты для bulk_remove_tags"""

    def test_bulk_remove_from_multiple_employees(self, employee, another_employee, department, tags, user):
        """Bulk удаление тегов у 3 сотрудников"""
        third_employee = Employee.objects.create(
            full_name="Третий Сотрудник",
            email="third@example.com",
            job_title="Дизайнер",
            birthday="1992-03-20",
            department=department
        )

        employee_ids = [employee.id, another_employee.id, third_employee.id]
        tag_ids = [tags['python'].id, tags['django'].id]

        bulk_assign_tags(employee_ids, tag_ids, user)

        for emp_id in employee_ids:
            assert EmployeeTag.objects.filter(employee_id=emp_id, is_deleted=False).count() == 2

        bulk_remove_tags(employee_ids, tag_ids, user)

        for emp_id in employee_ids:
            assert EmployeeTag.objects.filter(employee_id=emp_id, is_deleted=False).count() == 0
            assert EmployeeTag.all_objects.filter(employee_id=emp_id, is_deleted=True).count() == 2

    def test_bulk_remove_partially_existing_tags(self, employee, another_employee, tags, user):
        """Bulk удаление где некоторые теги не назначены"""
        assign_tags(employee, [tags['python'].id], user)

        employee_ids = [employee.id, another_employee.id]
        tag_ids = [tags['python'].id]

        bulk_remove_tags(employee_ids, tag_ids, user)

        employee_tag = EmployeeTag.all_objects.get(employee=employee, tag=tags['python'])
        assert employee_tag.is_deleted is True

        assert not EmployeeTag.objects.filter(employee=another_employee).exists()

    def test_bulk_remove_already_removed_tags(self, employee, another_employee, tags, user):
        """Bulk удаление уже удаленных тегов"""
        employee_ids = [employee.id, another_employee.id]
        tag_ids = [tags['python'].id]

        bulk_assign_tags(employee_ids, tag_ids, user)
        bulk_remove_tags(employee_ids, tag_ids, user)

        removed_at_first = EmployeeTag.all_objects.get(
            employee=employee, tag=tags['python']
        ).removed_at

        bulk_remove_tags(employee_ids, tag_ids, user)

        removed_at_second = EmployeeTag.all_objects.get(
            employee=employee, tag=tags['python']
        ).removed_at

        assert removed_at_first == removed_at_second


@pytest.mark.django_db
class TestAuditFields:
    """Тесты для полей аудита"""

    def test_assigned_by_is_correct(self, employee, tags, user, admin_user):
        """Проверка заполнения поля assigned_by"""
        assign_tags(employee, [tags['python'].id], user)

        employee_tag = EmployeeTag.objects.get(employee=employee, tag=tags['python'])
        assert employee_tag.assigned_by == user
        assert employee_tag.assigned_by != admin_user

    def test_removed_by_is_correct(self, employee, tags, user, admin_user):
        """Проверка заполнения поля removed_by"""
        assign_tags(employee, [tags['python'].id], user)

        remove_tags(employee, [tags['python'].id], admin_user)

        employee_tag = EmployeeTag.all_objects.get(employee=employee, tag=tags['python'])
        assert employee_tag.removed_by == admin_user
        assert employee_tag.removed_by != user

    def test_assigned_at_is_set(self, employee, tags, user):
        """Проверка автоматической установки assigned_at"""
        assign_tags(employee, [tags['python'].id], user)

        employee_tag = EmployeeTag.all_objects.get(employee=employee, tag=tags['python'])
        assert employee_tag.assigned_at is not None
        time_diff = timezone.now() - employee_tag.assigned_at
        assert time_diff.total_seconds() < 5

    def test_removed_at_is_set_on_delete(self, employee, tags, user):
        """Проверка установки removed_at при удалении"""
        assign_tags(employee, [tags['python'].id], user)

        import time
        time.sleep(1)

        remove_tags(employee, [tags['python'].id], user)

        employee_tag = EmployeeTag.all_objects.get(employee=employee, tag=tags['python'])
        assert employee_tag.removed_at is not None
        assert employee_tag.removed_at > employee_tag.assigned_at
