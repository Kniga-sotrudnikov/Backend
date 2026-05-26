from datetime import date

import pytest

from employees.models import Employee, Status
from employees.services import EmployeeCreate, EmployeeUpdate, archive_employee, create_employee, update_employee
from structure.models import Department


@pytest.mark.django_db
def test_create_employee_creates_employee_with_created_by(user):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )

    employee = create_employee(
        EmployeeCreate(
            full_name='Иван Иванов',
            job_title='Backend Developer',
            email='ivan@example.com',
            birthday=date(1990, 1, 1),
            department=department,
        ),
        created_by=user,
    )

    assert employee.pk is not None
    assert employee.full_name == 'Иван Иванов'
    assert employee.created_by == user


@pytest.mark.django_db
def test_update_employee_updates_fields_and_updated_by(user):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee = Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        birthday='1990-01-01',
        department=department,
    )

    updated_employee = update_employee(
        employee,
        EmployeeUpdate(
            full_name='Пётр Петров',
            job_title='Senior Backend Developer',
            phone='+79990000000',
        ),
        updated_by=user,
    )

    assert updated_employee.full_name == 'Пётр Петров'
    assert updated_employee.job_title == 'Senior Backend Developer'
    assert updated_employee.phone == '+79990000000'
    assert updated_employee.updated_by == user


@pytest.mark.django_db
def test_archive_employee_sets_archived_status(user):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee = Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        birthday='1990-01-01',
        department=department,
    )

    archived_employee = archive_employee(employee, updated_by=user)
    archived_employee.refresh_from_db()

    assert archived_employee.status == Status.ARCHIVED
    assert archived_employee.updated_by == user
    assert archived_employee.is_deleted is False
