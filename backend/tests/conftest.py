import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model



User = get_user_model()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def request_factory():
    from rest_framework.test import APIRequestFactory
    return APIRequestFactory()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123',
    )

@pytest.fixture
def hr(db):
    return User.objects.create_user(
        username='hr',
        email='hr@example.com',
        password='hrpassword123',
        role='hr_admin',
    )

@pytest.fixture
def employee(db):
    return User.objects.create_user(
        username='employee',
        email='employee@example.com',
        password='employeepassword123',
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def login_url():
    return reverse('token_obtain')


@pytest.fixture
def refresh_url():
    return reverse('token_refresh')


@pytest.fixture
def magic_link_verify_url():
    return reverse('magic_link')


@pytest.fixture
def data_for_success_auth(user):
    return {
        'email': user.email,
        'password': 'testpassword123'
    }


@pytest.fixture
def data_wrong_password(user):
    return {
        'email': user.email,
        'password': 'wrong_password123'
    }

