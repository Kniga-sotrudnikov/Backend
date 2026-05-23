import pytest


def test_ping_is_registered(celery_app_fixture):
    """Проверка регистрации ping через app.tasks."""
    assert "notifications.tasks.ping" in celery_app_fixture.tasks


def test_ping_returns_pong(celery_app_fixture):
    """ping() пишет pong и возвращает 'pong'."""
    app = celery_app_fixture

    app.conf.task_always_eager = True

    result = app.tasks["notifications.tasks.ping"].apply()

    assert result.get() == "pong"

    app.conf.task_always_eager = False