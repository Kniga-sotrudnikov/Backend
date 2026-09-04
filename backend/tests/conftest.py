import io

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient, APIRequestFactory

from employeebook.celery import app as celery_app
from employees.models import Employee
from favorites.models import Favorite
from structure.models import Department
from tags.models import Tag
from vacancies.models import Vacancy


User = get_user_model()


@pytest.fixture
def _django_setup():
    """Регистрирует задачи Celery для notifications и accounts."""
    celery_app.autodiscover_tasks(['notifications', 'accounts'], force=True)


@pytest.fixture
def api_client():
    """Неаутентифицированный API-клиент."""
    return APIClient()


@pytest.fixture
def request_factory():
    """Фабрика запросов DRF."""
    return APIRequestFactory()


@pytest.fixture
def user(db):
    """Обычный пользователь."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123',
    )


@pytest.fixture
def hr(db):
    """Пользователь с ролью hr_admin."""
    return User.objects.create_user(
        username='hr',
        email='hr@example.com',
        password='hrpassword123',
        role='hr_admin',
    )


@pytest.fixture
def employee(db):
    """Пользователь с ролью сотрудника."""
    return User.objects.create_user(
        username='employee',
        email='employee@example.com',
        password='employeepassword123',
    )


@pytest.fixture
def vacancy(db, department):
    """Тестовая вакансия."""

    return Vacancy.objects.create(
        title='Backend Dev',
        department=department,
        description='Python dev',
        status='open',
    )


@pytest.fixture
def vacancy_factory(db, department):
    """
    Factory для создания вакансий в тестах.
    """

    def create(**kwargs):
        return Vacancy.objects.create(
            title=kwargs.get("title", "Dev"),
            department=department,
            description="desc",
            status=kwargs.get("status", "open"),
        )
    return create


@pytest.fixture
def auth_client(api_client, user):
    """API-клиент, аутентифицированный как обычный пользователь."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def login_url():
    """URL получения JWT-токена."""
    return reverse('token_obtain')


@pytest.fixture
def refresh_url():
    """URL обновления JWT-токена."""
    return reverse('token_refresh')


@pytest.fixture
def favorite_url():
    """URL списка избранного текущего пользователя."""
    return reverse('favorites')


@pytest.fixture
def favorite_detail_url():
    """Фабрика URL детального эндпоинта избранного по employee_id."""
    return lambda employee_id: reverse('favorites_detail', args=[employee_id])


@pytest.fixture
def admin_favorite_url():
    """URL admin-эндпоинта избранного."""
    return reverse('admin-favorites')


@pytest.fixture
def admin_favorite_detail_url():
    """Фабрика URL детального admin-эндпоинта избранного по employee_id."""
    return lambda employee_id: reverse('admin-favorites-detail', args=[employee_id])


@pytest.fixture
def magic_link_verify_url():
    """URL верификации magic link."""
    return reverse('magic_link')


@pytest.fixture
def data_for_success_auth(user):
    """Корректные данные для аутентификации."""
    return {'email': user.email, 'password': 'testpassword123'}


@pytest.fixture
def data_wrong_password(user):
    """Данные для аутентификации с неверным паролем."""
    return {'email': user.email, 'password': 'wrong_password123'}


@pytest.fixture
def favorite_employee(employee_record, department):
    """Сотрудник для добавления в избранное."""
    return employee_record(
        full_name='Избранный сотрудник',
        job_title='Developer',
        email='favorite_employee@example.com',
        department=department,
    )


@pytest.fixture
def data_for_favorite(favorite_employee):
    """Payload для добавления сотрудника в избранное."""
    return {'employee_id': favorite_employee.id}


@pytest.fixture
def wrong_data_for_favorite():
    """Payload с несуществующим employee_id."""
    return {'employee_id': 999}


@pytest.fixture
def data_for_admin(favorite_employee):
    """Payload для HR: добавление в избранное с заметкой."""
    return {'employee_id': favorite_employee.id, 'note': 'Перспективный кандидат'}


@pytest.fixture
def hr_favorite(hr, favorite_employee):
    """Запись избранного, созданная HR-пользователем."""
    return Favorite.objects.create(user=hr, employee=favorite_employee, note='заметка')


@pytest.fixture
def user_favorite(db, user, favorite_employee):
    """Запись избранного, созданная обычным пользователем."""
    return Favorite.objects.create(user=user, employee=favorite_employee)


@pytest.fixture
def employee_record():
    """Фабрика для создания экземпляров Employee с произвольными параметрами."""
    def create(full_name, job_title, email, department, birthday='1990-01-01', status='active'):
        return Employee.objects.create(
            full_name=full_name,
            job_title=job_title,
            email=email,
            birthday=birthday,
            department=department,
            status=status,
        )
    return create


@pytest.fixture
def celery_app_fixture(_django_setup):
    """Инициализированное приложение Celery."""
    return celery_app


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
    return Department.objects.create(name='Backend', type=Department.Type.DEPARTMENT)


@pytest.fixture
def department_b(db):
    """Отдел Frontend для использования в тестах."""
    return Department.objects.create(name='Frontend', type=Department.Type.DEPARTMENT)


@pytest.fixture
def tag(db):
    """Тег Python."""
    return Tag.objects.create(name='Python')


@pytest.fixture
def three_employees(db, department):
    """Три сотрудника в отделе Backend."""
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
    """API-клиент, аутентифицированный как HR."""
    api_client.force_authenticate(user=hr)
    return api_client


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
    return reverse('employee-photo-upload', kwargs={'id': employee_instance.id})


@pytest.fixture
def matrix_data(db, department, tag, employee_instance):
    """Возвращает ID базовых сущностей для параметризованных тестов."""
    return {
        'dept_id': department.id,
        'tag_id': tag.id,
        'emp_id': employee_instance.id
    }
