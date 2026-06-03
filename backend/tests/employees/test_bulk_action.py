import pytest
from django.urls import reverse

from employees.models import Employee, Status
from tags.models import EmployeeTag


BULK_ACTION_URL = 'admin-employee-bulk-action'


@pytest.mark.django_db
def test_bulk_archive(hr_client, three_employees):
    """Все переданные сотрудники переводятся в статус ARCHIVED."""
    ids = [e.pk for e in three_employees]
    response = hr_client.post(
        reverse(BULK_ACTION_URL),
        data={'employee_ids': ids, 'action': 'archive', 'params': {}},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['total'] == 3
    assert response.data['success'] == 3
    assert response.data['failed'] == 0
    assert Employee.objects.filter(pk__in=ids, status=Status.ARCHIVED).count() == 3


@pytest.mark.django_db
def test_bulk_add_tag(hr_client, three_employees, tag):
    """Тег добавляется ко всем переданным сотрудникам."""
    ids = [e.pk for e in three_employees]
    response = hr_client.post(
        reverse(BULK_ACTION_URL),
        data={'employee_ids': ids, 'action': 'add_tag', 'params': {'tag': tag.pk}},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['success'] == 3
    assert response.data['failed'] == 0
    assert EmployeeTag.objects.filter(tag=tag, employee__in=three_employees).count() == 3


@pytest.mark.django_db
def test_bulk_remove_tag(hr_client, three_employees, tag, hr):
    """Тег снимается со всех переданных сотрудников."""
    for emp in three_employees:
        EmployeeTag.objects.create(tag=tag, employee=emp, assigned_by=hr)
    ids = [e.pk for e in three_employees]
    response = hr_client.post(
        reverse(BULK_ACTION_URL),
        data={'employee_ids': ids, 'action': 'remove_tag', 'params': {'tag': tag.pk}},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['success'] == 3
    assert response.data['failed'] == 0
    assert EmployeeTag.objects.filter(tag=tag, employee__in=three_employees).count() == 0


@pytest.mark.django_db
def test_bulk_change_department(hr_client, three_employees, department_b):
    """Все переданные сотрудники переводятся в новый отдел."""
    ids = [e.pk for e in three_employees]
    response = hr_client.post(
        reverse(BULK_ACTION_URL),
        data={'employee_ids': ids, 'action': 'change_department', 'params': {'department_id': department_b.pk}},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['success'] == 3
    assert response.data['failed'] == 0
    assert Employee.objects.filter(pk__in=ids, department=department_b).count() == 3


@pytest.mark.django_db
def test_bulk_action_partial_failure(hr_client, three_employees):
    """Один несуществующий employee_id не роняет остальные две записи."""
    valid_ids = [three_employees[0].pk, three_employees[1].pk]
    bad_id = 99999
    ids = valid_ids + [bad_id]
    response = hr_client.post(
        reverse(BULK_ACTION_URL),
        data={'employee_ids': ids, 'action': 'archive', 'params': {}},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['total'] == 3
    assert response.data['success'] == 2
    assert response.data['failed'] == 1
    assert response.data['details'][0]['employee_id'] == bad_id
    assert 'error' in response.data['details'][0]
    assert Employee.objects.filter(pk__in=valid_ids, status=Status.ARCHIVED).count() == 2
