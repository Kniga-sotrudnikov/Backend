from django.urls import reverse


def test_global_error_404_format(hr_client):
    """Проверка формата глобальной ошибки 404 Not Found от имени HR."""
    url = reverse('admin-employee-detail', kwargs={'pk': 999999})
    response = hr_client.get(url)

    assert response.status_code == 404
    data = response.data

    assert 'detail' in data
    assert 'code' in data
    assert 'field_errors' in data

    assert data['field_errors'] == {}
    assert data['code'] == 'error'

    # Проверяем как русский, так и английский варианты системного сообщения 404
    detail_lower = data['detail'].lower()
    assert any(
        msg in detail_lower
        for msg in ['не найден', 'найдена', 'matches the given query', 'not found']
    )


def test_validation_error_400_format(hr_client):
    """Проверка формата ошибки валидации 400 Bad Request при создании тега."""
    url = reverse('tag-list')
    response = hr_client.post(url, data={}, format='json')

    assert response.status_code == 400
    data = response.data

    assert 'detail' in data
    assert 'code' in data
    assert 'field_errors' in data

    assert data['code'] == 'validation_error'
    assert 'name' in data['field_errors']

    name_error = data['field_errors']['name']
    error_message = str(name_error).lower()

    # Поддерживаем оба языка для валидации обязательного поля
    assert any(
        msg in error_message
        for msg in ['обязательное', 'заполните', 'пустое', 'required', 'blank']
    )


def test_unauthorized_error_401_format(api_client):
    """Проверка формата ошибки 401 Unauthorized для анонимного пользователя."""
    url = reverse('employee-list')
    response = api_client.get(url)

    assert response.status_code == 401
    data = response.data

    assert 'detail' in data
    assert 'code' in data
    assert 'field_errors' in data
    assert data['field_errors'] == {}
