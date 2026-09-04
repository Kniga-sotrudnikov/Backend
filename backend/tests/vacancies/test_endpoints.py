from vacancies.models import Vacancy


def test_vacancy_list_requires_auth(client):
    """
    Проверяет, что список вакансий требует авторизации.
    """
    response = client.get('/api/v1/vacancies/')
    assert response.status_code == 401


def test_vacancy_list_returns_only_open_by_default(auth_client, vacancy_factory):
    """
    Проверяет, что по умолчанию возвращаются только открытые вакансии.
    """
    vacancy_factory(status='open')
    vacancy_factory(status='closed')

    response = auth_client.get('/api/v1/vacancies/')

    assert response.status_code == 200
    assert all(item['status'] == 'open' for item in response.data['results'])


def test_admin_vacancy_list_filters_and_orders(hr_client, department):
    """
    Проверяет фильтры и сортировку административного списка вакансий.
    """
    Vacancy.objects.create(
        title='Backend Developer',
        department=department,
        description='Python',
        status=Vacancy.Status.CLOSED,
    )
    Vacancy.objects.create(
        title='Android Developer',
        department=department,
        description='Kotlin',
        status=Vacancy.Status.CLOSED,
    )
    Vacancy.objects.create(
        title='HR Manager',
        department=department,
        description='People',
        status=Vacancy.Status.OPEN,
    )

    response = hr_client.get(
        '/api/v1/admin/vacancies/',
        data={'status': Vacancy.Status.CLOSED, 'search': 'Developer', 'ordering': 'title'},
    )

    assert response.status_code == 200
    assert [item['title'] for item in response.data['results']] == ['Android Developer', 'Backend Developer']


def test_vacancy_detail_contains_department(auth_client, vacancy):
    """
    Проверяет, что детальная информация о вакансии включает department.
    """
    response = auth_client.get(f'/api/v1/vacancies/{vacancy.id}/')

    assert response.status_code == 200
    assert 'department' in response.data


def test_hr_can_create_vacancy(api_client, hr, department):
    """
    Проверяет, что HR может создавать вакансии через admin endpoint.
    """
    api_client.force_authenticate(user=hr)

    payload = {
        'title': 'Backend Dev',
        'department': department.id,
        'description': 'Python dev',
        'status': 'open'
    }

    response = api_client.post('/api/v1/admin/vacancies/', payload)

    assert response.status_code == 201


def test_hr_can_update_vacancy(api_client, hr, vacancy):
    """
    Проверяет, что HR может обновлять вакансию.
    """
    api_client.force_authenticate(user=hr)

    response = api_client.patch(
        f'/api/v1/admin/vacancies/{vacancy.id}/',
        {'title': 'New title'},
    )

    assert response.status_code == 200


def test_hr_soft_delete_vacancy(api_client, hr, vacancy):
    """
    Проверяет мягкое удаление вакансии HR-ом.
    """
    api_client.force_authenticate(user=hr)

    response = api_client.delete(
        f'/api/v1/admin/vacancies/{vacancy.id}/'
    )

    assert response.status_code == 204

    vacancy.refresh_from_db()
    assert vacancy.is_deleted is True


def test_employee_cannot_access_admin_vacancies(api_client, employee):
    """
    Проверяет, что обычный сотрудник не имеет доступа к admin vacancy API.
    """
    api_client.force_authenticate(user=employee)

    response = api_client.get('/api/v1/admin/vacancies/')

    assert response.status_code == 403


def test_employee_cannot_create_vacancy(api_client, employee, department):
    """
    Проверяет, что обычный сотрудник не может создавать вакансии.
    """
    api_client.force_authenticate(user=employee)

    response = api_client.post(
        '/api/v1/admin/vacancies/',
        {
            'title': 'Test',
            'department': department.id,
            'description': 'x',
            'status': 'open'
        }
    )

    assert response.status_code == 403


def test_hr_cannot_update_vacancy_with_put(
    api_client,
    hr,
    vacancy,
):
    """
    Проверяет, что метод PUT недоступен для вакансий.
    """
    api_client.force_authenticate(user=hr)

    response = api_client.put(
        f'/api/v1/admin/vacancies/{vacancy.id}/',
        {
            'title': 'New title',
            'department': vacancy.department.id,
            'description': vacancy.description,
            'status': vacancy.status,
        },
    )

    assert response.status_code == 405
