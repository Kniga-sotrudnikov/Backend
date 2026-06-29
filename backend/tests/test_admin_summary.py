import pytest
from django.urls import reverse

from employees.models import Employee, Status
from structure.models import Department
from vacancies.models import Vacancy


@pytest.mark.django_db
def test_admin_summary_requires_hr(api_client, auth_client):
    url = reverse('admin-summary')

    unauthorized_response = api_client.get(url)
    employee_response = auth_client.get(url)

    assert unauthorized_response.status_code == 403
    assert employee_response.status_code == 403


@pytest.mark.django_db
def test_admin_summary_returns_header_counts(hr_client):
    active_direction = Department.objects.create(
        name='Технологии',
        type=Department.Type.DIRECTION,
    )
    Department.objects.create(
        name='Неактивное направление',
        type=Department.Type.DIRECTION,
        is_active=False,
    )
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
        parent=active_direction,
    )
    Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-summary@example.com',
        birthday='1990-01-01',
        department=department,
        status=Status.ACTIVE,
    )
    Employee.objects.create(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria-summary@example.com',
        birthday='1992-03-15',
        department=department,
        status=Status.ARCHIVED,
    )
    Vacancy.objects.create(
        title='Backend Developer',
        department=department,
        description='Python',
        status=Vacancy.Status.OPEN,
    )
    Vacancy.objects.create(
        title='Frontend Developer',
        department=department,
        description='React',
        status=Vacancy.Status.CLOSED,
    )

    response = hr_client.get(reverse('admin-summary'))

    assert response.status_code == 200
    assert response.data == {
        'employees_count': 1,
        'directions_count': 1,
        'vacancies_count': 1,
    }
