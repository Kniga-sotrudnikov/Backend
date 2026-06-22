import pytest
from django.urls import reverse
from vacancies.models import Vacancy

from employees.models import Employee
from favorites.models import Favorite
from structure.models import Department
from tags.models import EmployeeTag, Tag


@pytest.fixture
def query_count_dataset(db, user, hr):
    """Создаёт связанный набор данных для проверки количества SQL-запросов."""
    direction = Department.objects.create(name='Technology', type=Department.Type.DIRECTION)
    departments = [
        Department.objects.create(name=f'Department {index}', type=Department.Type.DEPARTMENT, parent=direction)
        for index in range(3)
    ]
    supervisor = Employee.objects.create(
        full_name='Руководитель Руководителей',
        job_title='Head of Engineering',
        email='supervisor@example.com',
        birthday='1990-01-01',
        department=departments[0],
        supervisor_role=departments[0],
    )
    tag = Tag.objects.create(name='Python')

    employees = []
    for index in range(6):
        employee = Employee.objects.create(
            full_name=f'Сотрудник {index}',
            job_title='Backend Developer',
            email=f'employee{index}@example.com',
            birthday='1991-01-01',
            department=departments[index % len(departments)],
            supervisor=supervisor,
            supervisor_role=departments[index % len(departments)],
            supervisor_photo=supervisor,
        )
        EmployeeTag.objects.create(employee=employee, tag=tag, assigned_by=hr)
        Favorite.objects.create(user=user, employee=employee)
        employees.append(employee)

    for index, department in enumerate(departments):
        Vacancy.objects.create(
            title=f'Vacancy {index}',
            department=department,
            description='Important role',
            status=Vacancy.Status.OPEN,
        )

    return {
        'direction': direction,
        'departments': departments,
        'employees': employees,
        'supervisor': supervisor,
    }


@pytest.mark.django_db
def test_employee_list_query_count(auth_client, query_count_dataset, django_assert_num_queries):
    """Список сотрудников выполняет фиксированное число запросов без N+1 по тегам."""
    with django_assert_num_queries(3):
        response = auth_client.get(reverse('employee-list'))

    assert response.status_code == 200
    assert response.data['count'] == len(query_count_dataset['employees']) + 1


@pytest.mark.django_db
def test_admin_employee_list_query_count(hr_client, query_count_dataset, django_assert_num_queries):
    """Admin-список сотрудников не плодит дополнительные запросы на связанных объектах."""
    with django_assert_num_queries(3):
        response = hr_client.get(reverse('admin-employee-list'))

    assert response.status_code == 200
    assert response.data['count'] == len(query_count_dataset['employees']) + 1


@pytest.mark.django_db
def test_employee_detail_query_count(auth_client, query_count_dataset, django_assert_num_queries):
    """Детальная карточка сотрудника использует предзагрузку связанных сущностей."""
    employee = query_count_dataset['employees'][0]

    with django_assert_num_queries(2):
        response = auth_client.get(reverse('employee-detail', kwargs={'pk': employee.id}))

    assert response.status_code == 200
    assert response.data['id'] == employee.id


@pytest.mark.django_db
def test_favorites_list_query_count(auth_client, query_count_dataset, django_assert_num_queries):
    """Избранное пользователя отдаётся без N+1 на карточках сотрудников."""
    with django_assert_num_queries(3):
        response = auth_client.get(reverse('favorites'))

    assert response.status_code == 200
    assert response.data['count'] == len(query_count_dataset['employees'])


@pytest.mark.django_db
def test_vacancies_list_query_count(auth_client, query_count_dataset, django_assert_num_queries):
    """Список вакансий не выполняет лишних запросов на подразделения."""
    with django_assert_num_queries(2):
        response = auth_client.get(reverse('vacancy-list'))

    assert response.status_code == 200
    assert response.data['count'] == len(query_count_dataset['departments'])


@pytest.mark.django_db
def test_departments_list_query_count(auth_client, query_count_dataset, django_assert_num_queries):
    """Список подразделений использует аннотацию employee_count без запросов в цикле."""
    with django_assert_num_queries(2):
        response = auth_client.get(reverse('department-list'))

    assert response.status_code == 200
    assert response.data['count'] == len(query_count_dataset['departments']) + 1


@pytest.mark.django_db
def test_org_structure_tree_query_count(auth_client, query_count_dataset, django_assert_num_queries):
    """Дерево оргструктуры собирается без рекурсивных SQL-запросов."""
    with django_assert_num_queries(1):
        response = auth_client.get(reverse('org-structure-tree'))

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_employee_birthdays_query_count(auth_client, query_count_dataset, django_assert_num_queries):
    """Список ближайших дней рождения фильтруется в БД, а не Python-циклом по queryset."""
    with django_assert_num_queries(1):
        response = auth_client.get(reverse('employee-birthdays'), {'days_ahead': 365})

    assert response.status_code == 200
    assert len(response.data) == len(query_count_dataset['employees']) + 1
