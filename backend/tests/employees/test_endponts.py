import pytest
from django.urls import reverse

from employees.models import Employee
from structure.models import Department


@pytest.mark.django_db
def test_employee_list_endpoint_returns_200(auth_client):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        birthday='1990-01-01',
        department=department,
    )

    response = auth_client.get(reverse('employee-list'))

    assert response.status_code == 200
    assert response.data['count'] == 1


@pytest.mark.django_db
def test_admin_employee_create_endpoint_returns_201(api_client, hr):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )

    payload = {
        'full_name': 'Мария Петрова',
        'job_title': 'HR Manager',
        'email': 'maria@example.com',
        'birthday': '1992-03-15',
        'department': department.id,
    }

    response = api_client.post(
        reverse('admin-employee-list'),
        data=payload,
        format='json',
    )

    assert response.status_code == 201
    employee = Employee.objects.get(email='maria@example.com')
    assert employee.full_name == payload['full_name']
    assert employee.created_by == hr
