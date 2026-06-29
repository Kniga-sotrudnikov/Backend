import pytest
from django.urls import reverse

from employees.models import Employee, InaccuracyReport
from employees.views import employee as employee_views
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
    assert response.data['id'] == employee.id
    assert response.data['department_id'] == department.id
    assert 'supervisor_detail' in response.data
    assert 'supervisor_photo_url' in response.data
    assert 'photo_original_url' in response.data


@pytest.mark.django_db
def test_admin_employee_patch_endpoint_returns_detail(api_client, hr, employee_record):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee = employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-patch@example.com',
        department=department,
    )

    response = api_client.patch(
        reverse('admin-employee-detail', kwargs={'pk': employee.id}),
        data={'job_title': 'Senior Backend Developer'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['id'] == employee.id
    assert response.data['job_title'] == 'Senior Backend Developer'
    assert response.data['department_id'] == department.id
    assert 'supervisor_detail' in response.data
    assert 'supervisor_photo_url' in response.data
    assert 'photo_original_url' in response.data


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


@pytest.mark.django_db
def test_report_inaccuracy_creates_report_returns_201(
    auth_client,
    user,
    employee_record,
):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee = employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-report@example.com',
        department=department,
    )
    response = auth_client.post(
        reverse('employee-report-inaccuracy', kwargs={'pk': employee.id}),
        data={'message': 'Неверно указан телефон'},
        format='json',
    )

    assert response.status_code == 201
    assert response.data['employee_id'] == employee.id
    assert response.data['message'] == 'Неверно указан телефон'
    assert response.data['status'] == 'new'
    assert response.data['created_at']

    report = InaccuracyReport.objects.get(id=response.data['id'])
    assert report.employee == employee
    assert report.created_by == user


@pytest.mark.django_db
def test_report_inaccuracy_returns_404_for_missing_employee(auth_client):
    response = auth_client.post(
        reverse('employee-report-inaccuracy', kwargs={'pk': 999999}),
        data={'message': 'Карточка не найдена'},
        format='json',
    )

    assert response.status_code == 404
    assert InaccuracyReport.objects.count() == 0


@pytest.mark.django_db
def test_report_inaccuracy_enqueues_hr_notification(
    auth_client,
    employee_record,
    django_capture_on_commit_callbacks,
    monkeypatch,
):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee = employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-task@example.com',
        department=department,
    )
    called_report_ids = []

    def fake_delay(report_id):
        called_report_ids.append(report_id)

    monkeypatch.setattr(employee_views.notify_hr_about_inaccuracy_report, 'delay', fake_delay)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(
            reverse('employee-report-inaccuracy', kwargs={'pk': employee.id}),
            data={'message': 'Неверно указан отдел'},
            format='json',
        )

    assert response.status_code == 201
    assert called_report_ids == [response.data['id']]
