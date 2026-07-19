import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import Role
from employees.models import Employee, Status
from structure.models import Department

User = get_user_model()


@pytest.fixture
def django_admin_user(db):
    """Создаёт суперпользователя для доступа к Django admin."""
    return User.objects.create_superuser(
        username='django-admin',
        email='django-admin@example.com',
        password='adminpass123',
        first_name='Django',
        last_name='Admin',
        role=Role.HR_ADMIN,
    )


@pytest.mark.django_db
def test_user_admin_add_form_contains_required_user_fields(client, django_admin_user):
    """Форма создания пользователя в admin содержит обязательные поля кастомной модели."""
    client.force_login(django_admin_user)

    response = client.get(reverse('admin:accounts_user_add'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="email"' in content
    assert 'name="username"' in content
    assert 'name="first_name"' in content
    assert 'name="last_name"' in content
    assert 'name="role"' in content


@pytest.mark.django_db
def test_user_admin_creates_user(client, django_admin_user):
    """Django admin создаёт пользователя через стандартный POST формы добавления."""
    client.force_login(django_admin_user)

    response = client.post(
        reverse('admin:accounts_user_add'),
        data={
            'email': 'new-user-admin@example.com',
            'username': 'new-user-admin',
            'first_name': 'Новый',
            'last_name': 'Пользователь',
            'role': Role.EMPLOYEE,
            'usable_password': 'true',
            'password1': 'strong-admin-pass-123',
            'password2': 'strong-admin-pass-123',
            '_save': 'Сохранить',
        },
    )

    assert response.status_code == 302
    user = User.objects.get(email='new-user-admin@example.com')
    assert user.username == 'new-user-admin'
    assert user.first_name == 'Новый'
    assert user.last_name == 'Пользователь'
    assert user.role == Role.EMPLOYEE
    assert user.check_password('strong-admin-pass-123')


@pytest.mark.django_db
def test_local_admin_changelists_are_available(client, django_admin_user):
    """Основные локальные changelist-страницы Django admin открываются."""
    client.force_login(django_admin_user)
    local_admin_models = [
        model
        for model in admin.site._registry
        if model._meta.app_label
        in {
            'accounts',
            'employees',
            'structure',
            'tags',
            'vacancies',
        }
    ]

    for model in local_admin_models:
        url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
        response = client.get(url)
        assert response.status_code == 200, url


@pytest.mark.django_db
def test_employee_admin_add_form_shows_only_creation_fields(client, django_admin_user):
    """Форма создания сотрудника показывает только поля, нужные при создании."""
    client.force_login(django_admin_user)

    response = client.get(reverse('admin:employees_employee_add'))

    assert response.status_code == 200
    assert response.context['title'] == 'Добавить сотрудника'
    assert set(response.context['adminform'].form.fields) == {
        'full_name',
        'job_title',
        'email',
        'birthday',
        'department',
        'phone',
        'city',
    }


@pytest.mark.django_db
def test_employee_admin_creates_employee_with_required_fields(client, django_admin_user):
    """Django admin создаёт сотрудника минимальным понятным набором полей."""
    client.force_login(django_admin_user)
    department = Department.objects.create(name='Backend', type=Department.Type.DEPARTMENT)

    response = client.post(
        reverse('admin:employees_employee_add'),
        data={
            'full_name': 'Иван Петров',
            'job_title': 'Backend-разработчик',
            'email': 'ivan.petrov-admin@example.com',
            'birthday': '1990-01-01',
            'department': department.id,
            'phone': '+79990000000',
            'city': 'Москва',
            '_save': 'Сохранить',
        },
    )

    assert response.status_code == 302
    employee = Employee.objects.get(email='ivan.petrov-admin@example.com')
    assert employee.full_name == 'Иван Петров'
    assert employee.department == department
    assert employee.status == Status.ACTIVE
    assert employee.created_by == django_admin_user


@pytest.mark.django_db
def test_employee_admin_change_form_hides_technical_fields(client, django_admin_user):
    """Форма редактирования сотрудника не показывает служебные поля soft-delete и аудита."""
    client.force_login(django_admin_user)
    department = Department.objects.create(name='Backend', type=Department.Type.DEPARTMENT)
    employee = Employee.objects.create(
        full_name='Иван Петров',
        job_title='Backend-разработчик',
        email='ivan.petrov-change-admin@example.com',
        birthday='1990-01-01',
        department=department,
    )

    response = client.get(reverse('admin:employees_employee_change', args=[employee.id]))

    assert response.status_code == 200
    form_fields = set(response.context['adminform'].form.fields)
    assert 'is_deleted' not in form_fields
    assert 'deleted_at' not in form_fields
    assert 'created_by' not in form_fields
    assert 'updated_by' not in form_fields


@pytest.mark.django_db
def test_employee_admin_shows_archived_and_hides_soft_deleted(client, django_admin_user):
    """Admin сотрудников показывает архивных и скрывает soft-deleted записи."""
    client.force_login(django_admin_user)
    department = Department.objects.create(name='Backend', type=Department.Type.DEPARTMENT)
    archived_employee = Employee.objects.create(
        full_name='Архивный Сотрудник',
        job_title='QA',
        email='archived-admin@example.com',
        birthday='1990-01-01',
        department=department,
        status=Status.ARCHIVED,
    )
    soft_deleted_employee = Employee.objects.create(
        full_name='Удалённый Сотрудник',
        job_title='QA',
        email='soft-deleted-admin@example.com',
        birthday='1990-01-01',
        department=department,
    )
    soft_deleted_employee.delete()

    response = client.get(reverse('admin:employees_employee_changelist'))

    assert response.status_code == 200
    content = response.content.decode()
    assert archived_employee.full_name in content
    assert soft_deleted_employee.full_name not in content
