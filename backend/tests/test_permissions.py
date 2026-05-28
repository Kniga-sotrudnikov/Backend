import pytest
from http import HTTPStatus

from django.contrib.auth.models import AnonymousUser
from rest_framework.test import force_authenticate

from tests.test_endpoints import IsHRView, IsOwnerOrHRView


@pytest.mark.django_db
def test_is_hr(hr, employee, request_factory):
    """HR проходит, сотрудник и аноним нет."""
    request = request_factory.get('/')
    force_authenticate(request, user=hr)
    assert IsHRView.as_view()(request).status_code == HTTPStatus.OK
    request = request_factory.get('/')
    force_authenticate(request, user=employee)
    assert IsHRView.as_view()(request).status_code == HTTPStatus.FORBIDDEN
    request = request_factory.get('/')
    request.user = AnonymousUser()
    assert IsHRView.as_view()(request).status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_is_owner_or_hr_hr_full_access(hr, request_factory):
    """HR имеет полный доступ."""
    request = request_factory.get('/')
    force_authenticate(request, user=hr)
    assert IsOwnerOrHRView.as_view()(request, user_id=999).status_code == HTTPStatus.OK
    request = request_factory.post('/')
    force_authenticate(request, user=hr)
    assert IsOwnerOrHRView.as_view()(request, user_id=999).status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_is_owner_or_hr_employee_can_only_get_own_profile(employee, request_factory):
    """Employee может смотреть только свой профиль, запись запрещена."""
    request = request_factory.get('/')
    force_authenticate(request, user=employee)
    assert IsOwnerOrHRView.as_view()(request, user_id=employee.id).status_code == HTTPStatus.OK
    assert IsOwnerOrHRView.as_view()(request, user_id=employee.id + 1).status_code == HTTPStatus.FORBIDDEN

    request = request_factory.post('/')
    force_authenticate(request, user=employee)
    assert IsOwnerOrHRView.as_view()(request, user_id=employee.id).status_code == HTTPStatus.FORBIDDEN

def test_is_owner_or_hr_anonymous_cannot_access(request_factory):
    """Аноним не проходит."""
    request = request_factory.get('/')
    request.user = AnonymousUser()
    assert IsOwnerOrHRView.as_view()(request, user_id=999).status_code == HTTPStatus.UNAUTHORIZED
