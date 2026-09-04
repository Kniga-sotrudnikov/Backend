import pytest

from employees.models import Employee
from structure.models import Department


@pytest.mark.django_db
def test_employee_direction_returns_parent_direction(user):
    direction = Department.objects.create(
        name='IT',
        type=Department.Type.DIRECTION,
    )

    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
        parent=direction,
    )

    employee = Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        birthday='1990-01-01',
        department=department,
        created_by=user,
    )

    assert employee.direction == direction
