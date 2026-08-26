import uuid
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient
from employees.models import Employee

User = get_user_model()


def test_employee_lifecycle_integration_flow(
    db, hr, user, department, tag, api_client, login_url, django_capture_on_commit_callbacks
):
    """
    Интеграционный тест: создание -> выдача -> архивация -> видимость в админке.

    Проверяет весь сквозной сценарий, включая автоматическую генерацию аккаунта
    пользователя, отправку почты после коммита транзакции и успешный вход по
    сгенерированному паролю.
    """

    hr_client = APIClient()
    hr_client.force_authenticate(user=hr)

    auth_client = APIClient()
    auth_client.force_authenticate(user=user)

    # ШАГ 1: HR создает сотрудника со связью с отделом (user не передается)
    unique_email = f'konstantin_{uuid.uuid4().hex[:8]}@company.com'
    create_url = reverse('admin-employee-list')
    employee_data = {
        'full_name': 'Константинопольский Константин Константинович',
        'job_title': 'Lead Backend Developer',
        'email': unique_email,
        'birthday': '1988-08-08',
        'department': department.id
    }

    with django_capture_on_commit_callbacks(execute=True):
        create_response = hr_client.post(create_url, data=employee_data, format='json')
    assert create_response.status_code == 201, f'Не удалось создать сотрудника: {create_response.data}'

    created_employee = Employee.objects.get(email=unique_email)
    employee_id = created_employee.id

    # Проверяем, что автоматически создался User с ролью employee
    assert created_employee.user is not None, 'User не был создан автоматически'
    assert created_employee.user.email == unique_email
    assert created_employee.user.role == 'employee'

    # Проверяем, что ушло ровно 1 приветственное письмо
    assert len(mail.outbox) == 1
    assert unique_email in mail.outbox[0].to
    assert 'Временный пароль:' in mail.outbox[0].body

    # Вытаскиваем пароль из письма и проверяем JWT-авторизацию нового сотрудника
    email_body = mail.outbox[0].body
    password_line = [line for line in email_body.split('\n') if 'Временный пароль:' in line]
    temporary_password = password_line[0].split(': ')[1].strip()

    login_payload = {
        'email': unique_email,
        'password': temporary_password
    }
    login_response = api_client.post(login_url, login_payload, format='json')
    assert login_response.status_code == 200, f'Новый сотрудник не смог войти: {login_response.data}'
    assert 'access' in login_response.data

    # ШАГ 2: HR привязывает тег к сотруднику (через массовое добавление тегов)
    assign_tag_url = reverse('bulk-add-tags')
    tag_data = {
        'employee_ids': (employee_id,),
        'tag_ids': (tag.id,)
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


def test_create_employee_with_existing_user_backward_compatibility(db, hr, employee, department):
    """
    Проверяет сохранение обратной совместимости.

    Если при создании карточки сотрудника явно передается id существующего
    пользователя, система не должна генерировать новый аккаунт, изменять пароль
    или отправлять приветственные письма.
    """
    hr_client = APIClient()
    hr_client.force_authenticate(user=hr)

    # Очищаем outbox, чтобы проверить, что писем точно не было
    mail.outbox.clear()

    create_url = reverse('admin-employee-list')
    employee_data = {
        'full_name': 'Существующий Юзер',
        'job_title': 'Frontend Developer',
        'email': employee.email,
        'birthday': '1990-01-01',
        'department': department.id,
        'user': employee.id
    }

    response = hr_client.post(create_url, data=employee_data, format='json')
    assert response.status_code == 201

    # Писем отправлено быть не должно
    assert len(mail.outbox) == 0

    # Пароль существующего пользователя из фиктуры не изменился
    assert employee.check_password('employeepassword123')


def test_create_employee_smtp_error_handling(db, hr, department, monkeypatch, django_capture_on_commit_callbacks):
    """
    Проверяет, что сбой отправки приветственного письма не мешает создать сотрудника.

    Письмо отправляется после коммита транзакции (transaction.on_commit), поэтому
    падение SMTP (в т.ч. когда Yandex SMTP уже отправил письмо, но оборвал
    соединение при закрытии) не должно откатывать уже сохранённых User и Employee.
    """
    hr_client = APIClient()
    hr_client.force_authenticate(user=hr)

    # Симулируем падение функции отправки почты send_mail
    def mock_send_mail(*args, **kwargs):
        raise Exception('SMTP Authentication Error')

    monkeypatch.setattr('employees.services.send_mail', mock_send_mail)

    create_url = reverse('admin-employee-list')
    employee_data = {
        'full_name': 'Сбойный Сотрудник',
        'job_title': 'DevOps',
        'email': 'fail_smtp@company.com',
        'birthday': '1992-12-12',
        'department': department.id
    }

    with django_capture_on_commit_callbacks(execute=True):
        response = hr_client.post(create_url, data=employee_data, format='json')

    # Сотрудник должен быть создан несмотря на сбой отправки письма
    assert response.status_code == 201, response.data

    # User и Employee должны быть сохранены в БД
    assert User.objects.filter(email='fail_smtp@company.com').exists()
    assert Employee.objects.filter(email='fail_smtp@company.com').exists()

    # Письмо не должно попасть в outbox, т.к. отправка упала
    assert not any(m.to == ['fail_smtp@company.com'] for m in mail.outbox)
