import pytest

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model

from employees.models import Employee
from structure.models import Department
from tags.models import Tag



User = get_user_model()

from employeebook.celery import app as celery_app


@pytest.fixture
def _django_setup():
    celery_app.autodiscover_tasks(['notifications'], force=True)


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def request_factory():
    from rest_framework.test import APIRequestFactory
    return APIRequestFactory()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123',
    )

@pytest.fixture
def hr(db):
    return User.objects.create_user(
        username='hr',
        email='hr@example.com',
        password='hrpassword123',
        role='hr_admin',
    )

@pytest.fixture
def employee(db):
    return User.objects.create_user(
        username='employee',
        email='employee@example.com',
        password='employeepassword123',
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def login_url():
    return reverse('token_obtain')


@pytest.fixture
def refresh_url():
    return reverse('token_refresh')


@pytest.fixture
def magic_link_verify_url():
    return reverse('magic_link')


@pytest.fixture
def data_for_success_auth(user):
    return {'email': user.email, 'password': 'testpassword123'}


@pytest.fixture
def data_wrong_password(user):
    return {'email': user.email, 'password': 'wrong_password123'}


@pytest.fixture
def celery_app_fixture(_django_setup):
    return celery_app


@pytest.fixture
def department(db):
    return Department.objects.create(name='Backend', type=Department.Type.DEPARTMENT)


@pytest.fixture
def department_b(db):
    return Department.objects.create(name='Frontend', type=Department.Type.DEPARTMENT)


@pytest.fixture
def tag(db):
    return Tag.objects.create(name='Python')


@pytest.fixture
def three_employees(db, department):
    return [
        Employee.objects.create(
            full_name=f'Сотрудник {i}',
            job_title='Developer',
            email=f'emp{i}@example.com',
            birthday='1990-01-01',
            department=department,
        )
        for i in range(3)
    ]


@pytest.fixture
def hr_client(api_client, hr):
    api_client.force_authenticate(user=hr)
    return api_client
