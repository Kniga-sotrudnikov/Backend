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


def test_department_create_accepts_head_id(hr_client):
    """HR может указать руководителя при создании подразделения."""
    direction = Department.objects.create(name='Технологии', type=Department.Type.DIRECTION)
    source_department = Department.objects.create(
        name='Platform',
        type=Department.Type.DEPARTMENT,
        parent=direction,
    )
    head = Employee.objects.create(
        full_name='Анна Руководитель',
        job_title='Team Lead',
        email='anna.head@example.com',
        birthday='1989-05-10',
        department=source_department,
    )

    response = hr_client.post(
        reverse('department-list'),
        data={
            'name': 'Backend',
            'type': Department.Type.DEPARTMENT,
            'parent': direction.id,
            'head_id': head.id,
            'display_order': 10,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    department = Department.objects.get(name='Backend')
    assert department.parent == direction
    assert department.head == head
    assert response.data['parent'] == direction.id
    assert response.data['head_id'] == head.id
    assert response.data['head'] == {
        'id': head.id,
        'full_name': head.full_name,
        'job_title': head.job_title,
    }


def test_department_patch_updates_head_id(hr_client):
    """HR может изменить или очистить руководителя подразделения."""
    department = Department.objects.create(name='Backend', type=Department.Type.DEPARTMENT)
    head_department = Department.objects.create(name='Leads', type=Department.Type.DEPARTMENT)
    head = Employee.objects.create(
        full_name='Иван Лид',
        job_title='Lead',
        email='ivan.lead@example.com',
        birthday='1988-04-20',
        department=head_department,
    )

    response = hr_client.patch(
        reverse('department-detail', kwargs={'pk': department.id}),
        data={'head_id': head.id},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    department.refresh_from_db()
    assert department.head == head
    assert response.data['head_id'] == head.id

    response = hr_client.patch(
        reverse('department-detail', kwargs={'pk': department.id}),
        data={'head_id': None},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    department.refresh_from_db()
    assert department.head is None
    assert response.data['head_id'] is None
    assert response.data['head'] is None


def test_department_patch_updates_parent(hr_client):
    """HR может изменить или очистить родительское подразделение."""
    old_direction = Department.objects.create(name='Технологии', type=Department.Type.DIRECTION)
    new_direction = Department.objects.create(name='Операции', type=Department.Type.DIRECTION)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
        parent=old_direction,
    )

    response = hr_client.patch(
        reverse('department-detail', kwargs={'pk': department.id}),
        data={'parent': new_direction.id},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    department.refresh_from_db()
    assert department.parent == new_direction
    assert response.data['parent'] == new_direction.id

    response = hr_client.patch(
        reverse('department-detail', kwargs={'pk': department.id}),
        data={'parent': None},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    department.refresh_from_db()
    assert department.parent is None
    assert response.data['parent'] is None


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
