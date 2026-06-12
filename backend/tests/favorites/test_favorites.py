from http import HTTPStatus

import pytest


@pytest.mark.django_db
def test_favorite_get_from_auth_user(auth_client, favorite_url):
    response = auth_client.get(favorite_url)
    assert response.status_code == HTTPStatus.OK
    assert 'count' in response.data
    assert 'next'in response.data
    assert 'previous' in response.data
    assert 'results' in response.data

@pytest.mark.django_db
def test_favorite_get_from_anonymous(api_client, favorite_url):
    response = api_client.get(favorite_url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED

@pytest.mark.django_db
def test_favorite_post_from_auth_user(auth_client, favorite_url, data_for_favorite, wrong_data_for_favorite):
    response = auth_client.post(favorite_url, data=data_for_favorite, format='json')
    assert response.status_code == HTTPStatus.CREATED
    assert 'employee_id' in response.data
    assert 'created_at' in response.data
    duplicate_favorite = auth_client.post(favorite_url, data=data_for_favorite, format='json')
    assert duplicate_favorite.status_code == HTTPStatus.BAD_REQUEST
    assert 'detail' in duplicate_favorite.data
    not_found_favorite = auth_client.post(favorite_url, data=wrong_data_for_favorite, format='json')
    assert not_found_favorite.status_code == HTTPStatus.BAD_REQUEST
    assert 'detail' in not_found_favorite.data

@pytest.mark.django_db
def test_favorite_post_from_anonymous(api_client, favorite_url):
    response = api_client.post(favorite_url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED

@pytest.mark.django_db
def test_favorite_delete_from_auth_user(auth_client, favorite_detail_url, user_favorite):
    url = favorite_detail_url(user_favorite.employee_id)
    response = auth_client.delete(url)
    assert response.status_code == HTTPStatus.NO_CONTENT

@pytest.mark.django_db
def test_favorite_delete_from_anonymous(api_client, favorite_detail_url, user_favorite):
    url = favorite_detail_url(user_favorite.employee_id)
    response = api_client.delete(url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED

