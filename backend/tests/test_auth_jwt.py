from http import HTTPStatus

import pytest


@pytest.mark.django_db
def test_success_login(api_client, login_url, data_for_success_auth, user):
    """Проверка успешого входа с корректными данными."""
    response = api_client.post(login_url, data_for_success_auth)
    assert response.status_code == HTTPStatus.OK
    assert 'access' in response.data
    assert 'refresh' in response.data
    user_data = response.data['user']
    assert user_data['id'] == user.id
    assert user_data['email'] == user.email
    assert user_data['role'] == user.role
    assert 'employee_id' in user_data

@pytest.mark.django_db
def test_login_wrong_password(api_client, login_url, data_wrong_password):
    """Проверка на не удачный вход с неверным паролем."""
    response = api_client.post(login_url, data_wrong_password)
    assert response.status_code == HTTPStatus.UNAUTHORIZED

@pytest.mark.django_db
def test_refresh_token(api_client, login_url, data_for_success_auth, refresh_url):
    """Проверка обновления токена."""
    login = api_client.post(login_url, data_for_success_auth)
    response = api_client.post(refresh_url, {'refresh': login.data['refresh']})
    assert response.status_code == HTTPStatus.OK
    assert 'access' in response.data
