import pytest
from django.urls import reverse
from rest_framework import status

from employees.models import Employee
from structure.models import Department

pytestmark = pytest.mark.django_db


def test_department_list_returns_employee_count(auth_client):
    """Список подразделений должен возвращать аннотированное число сотрудников."""
    direction = Department.objects.create(name='Технологии', type=Department.Type.DIRECTION)
    backend_department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
        parent=direction,
    )
    Department.objects.create(
        name='Frontend',
        type=Department.Type.DEPARTMENT,
        parent=direction,
    )
    Employee.objects.create(
        full_name='Иван Петров',
        job_title='Backend Developer',
        email='ivan.petrov@example.com',
        birthday='1990-01-01',
        department=backend_department,
    )
    Employee.objects.create(
        full_name='Мария Смирнова',
        job_title='Backend Developer',
        email='maria.smirnova@example.com',
        birthday='1991-02-02',
        department=backend_department,
    )

    response = auth_client.get(reverse('department-list'))

    assert response.status_code == status.HTTP_200_OK
    departments = response.data if isinstance(response.data, list) else response.data['results']
    backend_payload = next(item for item in departments if item['id'] == backend_department.id)
    assert backend_payload['employee_count'] == 2


def test_org_structure_tree_returns_employee_count(auth_client):
    """Дерево оргструктуры должно содержать число сотрудников на каждом узле."""
    direction = Department.objects.create(name='Операции', type=Department.Type.DIRECTION)
    hr_department = Department.objects.create(
        name='HR',
        type=Department.Type.DEPARTMENT,
        parent=direction,
    )
    Employee.objects.create(
        full_name='Елена Иванова',
        job_title='HR BP',
        email='elena.ivanova@example.com',
        birthday='1992-03-03',
        department=hr_department,
    )

    response = auth_client.get(reverse('org-structure-tree'))

    assert response.status_code == status.HTTP_200_OK
    direction_payload = next(item for item in response.data if item['id'] == direction.id)
    child_payload = next(item for item in direction_payload['children'] if item['id'] == hr_department.id)

    assert direction_payload['employee_count'] == 0
    assert child_payload['employee_count'] == 1
