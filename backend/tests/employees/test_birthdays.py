from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from employees.models import Employee
from notifications.models import BirthdayLog, BirthdayNotificationSettings
from notifications.tasks import check_upcoming_birthdays
from rest_framework import status


@pytest.mark.django_db
def test_birthday_endpoints_and_year_transition(api_client, three_employees, hr, department, user):
    """Тест эндпоинтов E5 и AB1 с динамическим расчетом дат и сортировкой."""
    today = timezone.now().date()

    emp1, emp2, emp3 = three_employees

    # Распределяем даты рождения для проверки сортировки
    date_5_days = today + timedelta(days=5)
    emp1.birthday = date(1995, date_5_days.month, date_5_days.day)
    emp1.status = 'active'
    emp1.is_deleted = False
    emp1.save()

    date_2_days = today + timedelta(days=2)
    emp2.birthday = date(1990, date_2_days.month, date_2_days.day)
    emp2.status = 'active'
    emp2.is_deleted = False
    emp2.save()

    # Сценарий для проверки перехода через год (2 января)
    target_jan_2 = date(today.year, 1, 2)
    if target_jan_2 <= today:
        target_jan_2 = date(today.year + 1, 1, 2)
    days_until_jan_2 = (target_jan_2 - today).days

    emp3.birthday = date(1988, 1, 2)
    emp3.status = 'active'
    emp3.is_deleted = False
    emp3.save()

    # --- 1. Публичный эндпоинт E5 (Обычный пользователь) ---
    api_client.force_authenticate(user=user)
    url_e5 = reverse('employee-birthdays')
    response = api_client.get(url_e5, {'days_ahead': days_until_jan_2 + 1})

    assert response.status_code == status.HTTP_200_OK
    emp3_data = next((item for item in response.data if item['id'] == emp3.id), None)
    assert emp3_data is not None
    assert emp3_data['birthday_display'] == '02.01'

    # --- 2. Админский эндпоинт AB1 (Связываем HR-пользователя с моделью Employee) ---
    Employee.objects.create(
        user=hr,
        full_name='HR Manager',
        job_title='HR',
        email=hr.email,
        birthday='1990-01-01',
        department=department,
    )
    api_client.force_authenticate(user=hr)

    response = api_client.get(reverse('admin-upcoming-birthdays'), {'days_ahead': 7})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 2

    # Проверяем сортировку по возрастанию days_until
    assert response.data[0]['employee']['id'] == emp2.id
    assert response.data[0]['days_until'] == 2

    assert response.data[1]['employee']['id'] == emp1.id
    assert response.data[1]['days_until'] == 5


@pytest.mark.django_db
def test_settings_endpoints_and_permissions(api_client, hr, department, user):
    """Тест GET/PUT эндпоинтов настроек и ограничений прав доступа."""
    url = reverse('birthday-settings')

    # Обычный пользователь получает 403 Forbidden
    api_client.force_authenticate(user=user)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Привязываем HR-карточку
    Employee.objects.create(
        user=hr,
        full_name='HR Manager',
        job_title='HR',
        email=hr.email,
        birthday='1990-01-01',
        department=department,
    )
    api_client.force_authenticate(user=hr)

    # Теперь GET работает успешно
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    # PUT-запрос запрещён
    payload = {
        'email_enabled': False,
        'days_before': 3,
        'recipients': ['hr_manager@company.com'],
    }
    response = api_client.put(url, data=payload, format='json')
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    # Patch-запрос работает успешно
    response = api_client.patch(url, data=payload, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['email_enabled'] is False


@pytest.mark.django_db
def test_celery_task_idempotency_and_disabled_mode(three_employees):
    """Подробный тест Celery-таски: идемпотентность и отключенный режим."""
    today = timezone.now().date()

    # Из фикстуры three_employees берем первого сотрудника
    emp = three_employees[0]

    days_before = 5
    target_date = today + timedelta(days=days_before)
    current_year = today.year

    emp.birthday = date(1990, target_date.month, target_date.day)
    emp.status = 'active'
    emp.is_deleted = False
    emp.save()

    settings = BirthdayNotificationSettings.load()
    settings.email_enabled = True
    settings.recipients = ['hr@company.com']
    settings.days_before = days_before
    settings.save()

    # Запуск 1: Уведомление должно успешно отправиться
    result_1 = check_upcoming_birthdays()
    assert 'Успешно отправлено уведомлений: 1' in result_1
    assert BirthdayLog.objects.filter(employee=emp, year=current_year).exists()

    # Запуск 2: Идемпотентность блокирует повторную отправку
    result_2 = check_upcoming_birthdays()
    assert 'Успешно отправлено уведомлений: 0' in result_2

    # Запуск 3: Если уведомления выключены
    settings.email_enabled = False
    settings.save()

    BirthdayLog.objects.all().delete()
    result_3 = check_upcoming_birthdays()
    assert 'Уведомления отключены' in result_3
