import uuid
from django.urls import reverse
from rest_framework.test import APIClient
from employees.models import Employee


def test_employee_lifecycle_integration_flow(db, hr, user, department, tag):
    """Интеграционный тест: создание -> выдача -> архивация -> видимость в админке."""

    hr_client = APIClient()
    hr_client.force_authenticate(user=hr)

    auth_client = APIClient()
    auth_client.force_authenticate(user=user)

    # ШАГ 1: HR создает сотрудника со связью с отделом
    unique_email = f'konstantin_{uuid.uuid4().hex[:8]}@company.com'
    create_url = reverse('admin-employee-list')
    employee_data = {
        'full_name': 'Константинопольский Константин Константинович',
        'job_title': 'Lead Backend Developer',
        'email': unique_email,
        'birthday': '1988-08-08',
        'department': department.id
    }

    create_response = hr_client.post(create_url, data=employee_data, format='json')
    assert create_response.status_code == 201, f'Не удалось создать сотрудника: {create_response.data}'

    created_employee = Employee.objects.get(email=unique_email)
    employee_id = created_employee.id

    # ШАГ 2: HR привязывает тег к сотруднику (через массовое добавление тегов)
    assign_tag_url = reverse('bulk-add-tags')
    tag_data = {
        'employee_ids': [employee_id],
        'tag_ids': [tag.id]
    }

    tag_response = hr_client.post(assign_tag_url, data=tag_data, format='json')
    assert tag_response.status_code == 200, f'Не удалось привязать тег: {tag_response.data}'

    # ШАГ 3: Обычный пользователь запрашивает публичный список (Проверка выдачи)
    public_list_url = reverse('employee-list')
    public_response = auth_client.get(public_list_url)
    assert public_response.status_code == 200

    data = public_response.data
    public_employees = data.get('results', data) if isinstance(data, dict) else data

    created_emp_in_public = next(
        (emp for emp in public_employees if isinstance(emp, dict) and emp.get('id') == employee_id),
        None
    )

    assert created_emp_in_public is not None, f'Сотрудник не найден в паблике. Ответ: {data}'
    assert created_emp_in_public['full_name'] == employee_data['full_name']

    # Проверяем имя департамента
    assert created_emp_in_public.get('department_name') == department.name

    # Проверяем наличие привязанного тега в списке
    tags_field = created_emp_in_public.get('tags', [])
    tag_ids = [t['id'] for t in tags_field if isinstance(t, dict) and 'id' in t]
    assert tag.id in tag_ids

    # ШАГ 4: HR архивирует сотрудника
    detail_admin_url = reverse('admin-employee-detail', kwargs={'pk': employee_id})
    delete_response = hr_client.delete(detail_admin_url)
    assert delete_response.status_code == 204, 'Архивация (удаление) не вернула 204'

    # ШАГ 5: Обычный пользователь проверяет публичный список — сотрудник должен исчезнуть
    public_response_after = auth_client.get(public_list_url)
    data_after = public_response_after.data
    public_employees_after = data_after.get('results', data_after) if isinstance(data_after, dict) else data_after

    is_visible_in_public = any(
        isinstance(emp, dict) and emp.get('id') == employee_id for emp in public_employees_after
    )
    assert not is_visible_in_public, 'Архивированный сотрудник всё ещё виден в паблике!'

    # ШАГ 6: HR проверяет админский список с фильтром по архивированным
    admin_list_url = reverse('admin-employee-list')
    admin_response = hr_client.get(admin_list_url, data={'status': 'archived'})
    assert admin_response.status_code == 200

    admin_data = admin_response.data
    admin_employees = admin_data.get('results', admin_data) if isinstance(admin_data, dict) else admin_data

    archived_emp_in_admin = next(
        (emp for emp in admin_employees if isinstance(emp, dict) and emp.get('id') == employee_id),
        None
    )

    assert archived_emp_in_admin is not None, f'Сотрудник не найден в админке. Ответ: {admin_data}'
