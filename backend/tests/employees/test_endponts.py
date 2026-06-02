import pytest
from django.urls import reverse

from employees.models import Employee
from structure.models import Department
from tags.models import Tag, EmployeeTag


@pytest.mark.django_db
def test_employee_list_endpoint_returns_200(auth_client, employee_record):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
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


@pytest.mark.parametrize(
    ('query_params_builder', 'expected_name'),
    [
        (lambda data: {'search': 'Петр'}, {'Петр Иванов', 'Мария Петрова'}),
        (lambda data: {'search': 'dev'}, {'Петр Иванов'}),
        (lambda data: {'job_title': 'Backend Developer'}, {'Петр Иванов'}),
        (lambda data: {'department_id': data['backend_department'].id}, {'Петр Иванов'}),
        (lambda data: {'direction_id': data['it_direction'].id}, {'Петр Иванов'}),
    ],
)
@pytest.mark.django_db
def test_employee_list_filters(auth_client, employee_record, query_params_builder, expected_name):
    it_direction = Department.objects.create(
        name='IT',
        type=Department.Type.DIRECTION,
    )
    hr_direction = Department.objects.create(
        name='People',
        type=Department.Type.DIRECTION,
    )
    backend_department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
        parent=it_direction,
    )
    hr_department = Department.objects.create(
        name='HR',
        type=Department.Type.DEPARTMENT,
        parent=hr_direction,
    )
    employee_record(
        full_name='Петр Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        department=backend_department,
    )
    employee_record(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria@example.com',
        department=hr_department,
    )

    query_params = query_params_builder(
        {
            'it_direction': it_direction,
            'backend_department': backend_department,
        }
    )
    response = auth_client.get(reverse('employee-list'), data=query_params)

    assert response.status_code == 200
    assert response.data['count'] == len(expected_name)
    assert {item['full_name'] for item in response.data['results']} == expected_name


@pytest.mark.django_db
def test_employee_list_filters_by_tag(auth_client, employee_record):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    python_tag = Tag.objects.create(name='Python')
    django_tag = Tag.objects.create(name='Django')
    backend_employee = employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        department=department,
    )
    hr_employee = employee_record(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria@example.com',
        department=department,
    )
    EmployeeTag.objects.create(employee=backend_employee, tag=python_tag)
    EmployeeTag.objects.create(employee=backend_employee, tag=django_tag)
    EmployeeTag.objects.create(employee=hr_employee, tag=django_tag)

    response = auth_client.get(
        reverse('employee-list'),
        data=[('tag', python_tag.id), ('tag', django_tag.id)],
    )

    assert response.status_code == 200
    assert response.data['count'] == 2


@pytest.mark.django_db
def test_admin_list_employee_filters_by_archived_status(api_client, hr, employee_record):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        department=department,
        status='active',
    )
    employee_record(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria@example.com',
        birthday='1992-03-15',
        department=department,
        status='archived',
    )
    response = api_client.get(reverse('admin-employee-list'), data={'status': 'archived'})

    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['status'] == 'archived'


@pytest.mark.parametrize(
    ('ordering', 'expected_results'),
    [
        ('full_name', ['Анна Петрова', 'Иван Иванов', 'Петр Петров']),
        ('-full_name', ['Петр Петров', 'Иван Иванов', 'Анна Петрова']),
        ('birthday', ['Петр Петров', 'Иван Иванов', 'Анна Петрова']),
        ('-birthday', ['Анна Петрова', 'Иван Иванов', 'Петр Петров'])
    ]
)
def test_employee_list_ordering(auth_client, employee_record, ordering, expected_results):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan@example.com',
        birthday='1990-01-01',
        department=department,
    )
    employee_record(
        full_name='Анна Петрова',
        job_title='Backend Developer',
        email='anna@example.com',
        birthday='1992-03-15',
        department=department,
    )
    employee_record(
        full_name='Петр Петров',
        job_title='Backend Developer',
        email='petr@example.com',
        birthday='1988-07-20',
        department=department,
    )
    response = auth_client.get(reverse('employee-list'), data={'ordering': ordering})

    assert response.status_code == 200
    assert [item['full_name'] for item in response.data['results']] == expected_results
