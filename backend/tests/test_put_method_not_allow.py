import pytest


@pytest.mark.parametrize("url", [
    "/api/v1/admin/vacancies/",
    "/api/v1/admin/employees/",
    "/api/v1/admin/birthdays/settings/",
])
def test_put_not_allowed(api_client, hr, url):
    """Общая проверка PUT метода."""

    api_client.force_authenticate(user=hr)

    response = api_client.put(url, {})

    assert response.status_code == 405
