from http import HTTPStatus

import pytest


@pytest.mark.django_db
def test_favorite_get_from_auth_user(auth_client, favorite_url):
    """Авторизованный пользователь получает пагинированный список избранного."""
    response = auth_client.get(favorite_url)
    assert response.status_code == HTTPStatus.OK
    assert 'count' in response.data
    assert 'next' in response.data
    assert 'previous' in response.data
    assert 'results' in response.data


@pytest.mark.django_db
def test_favorite_get_from_anonymous(api_client, favorite_url):
    """Анонимный запрос возвращает 401."""
    response = api_client.get(favorite_url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_favorite_post_from_auth_user(auth_client, favorite_url, data_for_favorite):
    """Добавление сотрудника в избранное возвращает 201 с employee_id и created_at."""
    response = auth_client.post(favorite_url, data=data_for_favorite, format='json')
    assert response.status_code == HTTPStatus.CREATED
    assert 'employee_id' in response.data
    assert 'created_at' in response.data


@pytest.mark.django_db
def test_favorite_post_duplicate_returns_400(auth_client, favorite_url, data_for_favorite):
    """Повторное добавление того же сотрудника возвращает 400."""
    auth_client.post(favorite_url, data=data_for_favorite, format='json')
    duplicate = auth_client.post(favorite_url, data=data_for_favorite, format='json')
    assert duplicate.status_code == HTTPStatus.BAD_REQUEST
    assert 'detail' in duplicate.data


@pytest.mark.django_db
def test_favorite_post_not_found_returns_404(auth_client, favorite_url, wrong_data_for_favorite):
    """Добавление несуществующего сотрудника возвращает 404."""
    response = auth_client.post(favorite_url, data=wrong_data_for_favorite, format='json')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'detail' in response.data


@pytest.mark.django_db
def test_favorite_post_from_anonymous(api_client, favorite_url):
    """Анонимный POST возвращает 401."""
    response = api_client.post(favorite_url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_favorite_delete_from_auth_user(auth_client, favorite_detail_url, user_favorite):
    """Удаление своего избранного возвращает 204."""
    url = favorite_detail_url(user_favorite.employee_id)
    response = auth_client.delete(url)
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_favorite_delete_from_anonymous(api_client, favorite_detail_url, user_favorite):
    """Анонимный DELETE возвращает 401."""
    url = favorite_detail_url(user_favorite.employee_id)
    response = api_client.delete(url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_hr_favorite_post_with_note(hr_client, admin_favorite_url, data_for_admin):
    """HR добавляет сотрудника в избранное с заметкой, ответ содержит note."""
    response = hr_client.post(admin_favorite_url, data=data_for_admin, format='json')
    assert response.status_code == HTTPStatus.CREATED
    assert 'employee_id' in response.data
    assert 'note' in response.data
    assert 'created_at' in response.data


@pytest.mark.django_db
def test_hr_favorite_delete(hr_client, admin_favorite_detail_url, hr_favorite):
    """HR удаляет запись из избранного, возвращает 204."""
    url = admin_favorite_detail_url(hr_favorite.employee_id)
    response = hr_client.delete(url)
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_admin_favorites_forbidden_for_regular_user(auth_client, admin_favorite_url):
    """Обычный пользователь не имеет доступа к admin-эндпоинту избранного."""
    response = auth_client.get(admin_favorite_url)
    assert response.status_code == HTTPStatus.FORBIDDEN
