from io import BytesIO
from zipfile import ZipFile

import pytest
from django.urls import reverse

from employees.models import Employee, InaccuracyReport
from employees.views import employee as employee_views
from structure.models import Department
from tags.models import EmployeeTag, Tag


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
    assert employee.role_description == []
    assert response.data['role_description'] == []
    assert response.data['id'] == employee.id
    assert response.data['department_id'] == department.id
    assert 'supervisor_detail' in response.data
    assert 'supervisor_photo_url' in response.data
    assert 'photo_original_url' in response.data


@pytest.mark.django_db
def test_admin_employee_create_accepts_role_description_list(api_client, hr):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )

    response = api_client.post(
        reverse('admin-employee-list'),
        data={
            'full_name': 'Мария Петрова',
            'job_title': 'HR Manager',
            'email': 'maria-role@example.com',
            'birthday': '1992-03-15',
            'department': department.id,
            'role_description': ['Подбор', 'Адаптация'],
        },
        format='json',
    )

    assert response.status_code == 201
    employee = Employee.objects.get(email='maria-role@example.com')
    assert employee.role_description == ['Подбор', 'Адаптация']
    assert response.data['role_description'] == ['Подбор', 'Адаптация']


@pytest.mark.django_db
def test_admin_employee_create_accepts_open_tag_names(api_client, hr):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    tag_names = ['#запуск-нового-направления', '#английский-язык-B1+']

    response = api_client.post(
        reverse('admin-employee-list'),
        data={
            'full_name': 'Мария Петрова',
            'job_title': 'HR Manager',
            'email': 'maria-tags@example.com',
            'birthday': '1992-03-15',
            'department': department.id,
            'tags': tag_names,
        },
        format='json',
    )

    assert response.status_code == 201
    employee = Employee.objects.get(email='maria-tags@example.com')
    assert set(Tag.objects.filter(name__in=tag_names).values_list('name', flat=True)) == set(tag_names)
    assert set(employee.employee_tags.filter(is_deleted=False).values_list('tag__name', flat=True)) == set(tag_names)
    assert set(tag['name'] for tag in response.data['tags']) == set(tag_names)
    assert all(employee_tag.assigned_by == hr for employee_tag in employee.employee_tags.all())


@pytest.mark.django_db
def test_admin_employee_create_rejects_role_description_object(api_client, hr):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )

    response = api_client.post(
        reverse('admin-employee-list'),
        data={
            'full_name': 'Мария Петрова',
            'job_title': 'HR Manager',
            'email': 'maria-role-invalid@example.com',
            'birthday': '1992-03-15',
            'department': department.id,
            'role_description': {},
        },
        format='json',
    )

    assert response.status_code == 400
    assert 'role_description' in response.data['field_errors']


@pytest.mark.django_db
def test_admin_employee_patch_replaces_tags_with_names(api_client, hr, employee_record):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    old_tag = Tag.objects.create(name='Legacy')
    existing_tag = Tag.objects.create(name='Python')
    employee = employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-tags@example.com',
        department=department,
    )
    EmployeeTag.objects.create(employee=employee, tag=old_tag, assigned_by=hr)

    response = api_client.patch(
        reverse('admin-employee-detail', kwargs={'pk': employee.id}),
        data={'tags': [existing_tag.name, '#пилотный-проект']},
        format='json',
    )

    assert response.status_code == 200
    active_tag_names = set(employee.employee_tags.filter(is_deleted=False).values_list('tag__name', flat=True))
    assert active_tag_names == {'Python', '#пилотный-проект'}
    assert EmployeeTag.all_objects.get(employee=employee, tag=old_tag).is_deleted is True
    assert set(tag['name'] for tag in response.data['tags']) == active_tag_names


@pytest.mark.django_db
def test_admin_employee_create_rejects_numeric_tags(api_client, hr):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )

    response = api_client.post(
        reverse('admin-employee-list'),
        data={
            'full_name': 'Мария Петрова',
            'job_title': 'HR Manager',
            'email': 'maria-numeric-tags@example.com',
            'birthday': '1992-03-15',
            'department': department.id,
            'tags': [1],
        },
        format='json',
    )

    assert response.status_code == 400
    assert 'tags' in response.data['field_errors']


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


@pytest.mark.django_db
def test_employee_detail_returns_personal_contacts(auth_client):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee = Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-detail@example.com',
        phone='+79990000000',
        personal_phone='+79990000001',
        personal_email='ivan.personal@example.com',
        birthday='1990-01-01',
        department=department,
    )

    response = auth_client.get(reverse('employee-detail', kwargs={'pk': employee.id}))

    assert response.status_code == 200
    assert response.data['personal_phone'] == '+79990000001'
    assert response.data['personal_email'] == 'ivan.personal@example.com'


@pytest.mark.django_db
def test_admin_employee_detail_returns_personal_contacts(api_client, hr):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee = Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-admin-detail@example.com',
        phone='+79990000000',
        personal_phone='+79990000001',
        personal_email='ivan.personal@example.com',
        birthday='1990-01-01',
        department=department,
    )

    response = api_client.get(reverse('admin-employee-detail', kwargs={'pk': employee.id}))

    assert response.status_code == 200
    assert response.data['personal_phone'] == '+79990000001'
    assert response.data['personal_email'] == 'ivan.personal@example.com'


@pytest.mark.django_db
def test_admin_employee_patch_updates_extended_profile_fields(api_client, hr, employee_record):
    api_client.force_authenticate(user=hr)
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    supervisor_role = Department.objects.create(
        name='Team Lead',
        type=Department.Type.DEPARTMENT,
    )
    supervisor = employee_record(
        full_name='Анна Руководитель',
        job_title='Team Lead',
        email='anna-lead@example.com',
        department=department,
    )
    supervisor_photo = employee_record(
        full_name='Ирина Фото',
        job_title='Head of Engineering',
        email='irina-photo@example.com',
        department=department,
    )
    employee = employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-extended-patch@example.com',
        department=department,
    )

    response = api_client.patch(
        reverse('admin-employee-detail', kwargs={'pk': employee.id}),
        data={
            'personal_phone': '+79990000001',
            'personal_email': 'ivan.personal@example.com',
            'supervisor': supervisor.id,
            'supervisor_role': supervisor_role.id,
            'supervisor_photo': supervisor_photo.id,
            'city': 'Москва',
            'employment_status': 'remote',
            'crm_profile': 'https://crm.example.com/profiles/ivan',
            'social_network': 'https://social.example.com/ivan',
            'resume_link': 'https://example.com/resume/ivan',
        },
        format='json',
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.personal_phone == '+79990000001'
    assert employee.personal_email == 'ivan.personal@example.com'
    assert employee.supervisor == supervisor
    assert employee.supervisor_role == supervisor_role
    assert employee.supervisor_photo == supervisor_photo
    assert employee.city == 'Москва'
    assert employee.employment_status == 'remote'
    assert employee.crm_profile == 'https://crm.example.com/profiles/ivan'
    assert employee.social_network == 'https://social.example.com/ivan'
    assert employee.resume_link == 'https://example.com/resume/ivan'


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
def test_employee_list_filters_by_city_case_insensitive(auth_client):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-city@example.com',
        birthday='1990-01-01',
        department=department,
        city='Москва',
    )
    Employee.objects.create(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria-city@example.com',
        birthday='1992-03-15',
        department=department,
        city='Казань',
    )

    response = auth_client.get(reverse('employee-list'), data={'city': 'москва'})

    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['full_name'] == 'Иван Иванов'


@pytest.mark.django_db
def test_employee_list_filters_by_employment_status(auth_client):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-remote@example.com',
        birthday='1990-01-01',
        department=department,
        employment_status='remote',
    )
    Employee.objects.create(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria-vacation@example.com',
        birthday='1992-03-15',
        department=department,
        employment_status='vacation',
    )

    response = auth_client.get(reverse('employee-list'), data={'employment_status': 'remote'})

    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['full_name'] == 'Иван Иванов'


@pytest.mark.django_db
def test_admin_list_and_export_filter_by_city_and_employment_status(hr_client):
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    Employee.objects.create(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-admin-filter@example.com',
        birthday='1990-01-01',
        department=department,
        city='Москва',
        employment_status='remote',
    )
    Employee.objects.create(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria-admin-filter@example.com',
        birthday='1992-03-15',
        department=department,
        city='Москва',
        employment_status='working',
    )

    params = {'city': 'москва', 'employment_status': 'remote'}
    list_response = hr_client.get(reverse('admin-employee-list'), data=params)
    export_response = hr_client.get(reverse('admin-employee-export'), data=params)

    assert list_response.status_code == 200
    assert list_response.data['count'] == 1
    assert list_response.data['results'][0]['full_name'] == 'Иван Иванов'
    assert export_response.status_code == 200
    with ZipFile(BytesIO(export_response.content)) as archive:
        sheet_xml = archive.read('xl/worksheets/sheet1.xml').decode()
    assert 'Иван Иванов' in sheet_xml
    assert 'Мария Петрова' not in sheet_xml


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
        ('-birthday', ['Анна Петрова', 'Иван Иванов', 'Петр Петров']),
    ],
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
def test_admin_employee_list_ordering(hr_client, employee_record):
    """Административный список сотрудников поддерживает сортировку."""
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-admin-order@example.com',
        birthday='1990-01-01',
        department=department,
    )
    employee_record(
        full_name='Анна Петрова',
        job_title='Backend Developer',
        email='anna-admin-order@example.com',
        birthday='1992-03-15',
        department=department,
    )

    response = hr_client.get(reverse('admin-employee-list'), data={'ordering': 'full_name'})

    assert response.status_code == 200
    assert [item['full_name'] for item in response.data['results']] == ['Анна Петрова', 'Иван Иванов']


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
