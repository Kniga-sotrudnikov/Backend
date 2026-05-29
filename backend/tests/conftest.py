import io
from PIL import Image

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory

from employees.models import Employee
from structure.models import Department


User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def request_factory():
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
    return {
        'email': user.email,
        'password': 'testpassword123'
    }


@pytest.fixture
def data_wrong_password(user):
    return {
        'email': user.email,
        'password': 'wrong_password123'
    }


@pytest.fixture(scope="session")
def dummy_image_factory():
    """Фабрика для генерации изображений в памяти с настраиваемыми размерами."""

    def _create_image(width=1200, height=800, extension='JPEG'):
        file_obj = io.BytesIO()
        image = Image.new('RGB', (width, height), color='blue')
        image.save(file_obj, format=extension)
        file_obj.seek(0)
        return file_obj.read()
    return _create_image


@pytest.fixture
def department(db):
    """Фикстура для создания обязательного отдела."""
    return Department.objects.create(name='Тестовый отдел', type='department')


@pytest.fixture
def employee_instance(department):
    """Фикстура для создания карточки сотрудника (инстанс модели Employee)."""
    return Employee.objects.create(
        full_name='Иванов Иван Иванович',
        job_title='Разработчик',
        email='ivanov_photo@company.com',
        birthday='1990-01-01',
        department=department
    )


@pytest.fixture
def upload_url(employee_instance):
    """Фикстура для получения URL эндпоинта загрузки фото конкретного сотрудника."""
    from django.urls import reverse
    return reverse('employee-photo-upload', kwargs={'id': employee_instance.id})
