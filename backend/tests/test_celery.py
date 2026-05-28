import pytest


def test_ping_is_registered(celery_app_fixture):
    """Проверка регистрации ping через app.tasks."""
    assert 'notifications.tasks.ping' in celery_app_fixture.tasks


def test_ping_returns_pong(celery_app_fixture):
    """ping() пишет pong и возвращает 'pong'."""
    result = celery_app_fixture.tasks['notifications.tasks.ping'].apply()
    assert result.get() == 'pong'
