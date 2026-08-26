import logging
from unittest import mock

import pytest
from django.urls import reverse

from accounts.models import MagicLinkToken
from accounts.tasks import send_magic_link_email


@pytest.fixture
def magic_link_request_url():
    """URL запроса magic link."""
    return reverse('magic_link')


def test_task_is_registered(celery_app_fixture):
    """Задача отправки magic-link зарегистрирована в приложении Celery."""
    assert 'accounts.tasks.send_magic_link_email' in celery_app_fixture.tasks


def test_task_sends_email_with_link(db, settings, mailoutbox, caplog):
    """Задача отправляет одно письмо, тело которого содержит ссылку, без токена в логах."""
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.DEFAULT_FROM_EMAIL = 'noreply@example.com'
    link = 'https://example.com/auth/login/magic-link?token=SECRET_RAW_TOKEN'

    with caplog.at_level(logging.INFO):
        send_magic_link_email('user@example.com', link)

    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.subject == 'Ссылка для входа'
    assert message.to == ['user@example.com']
    assert message.from_email == 'noreply@example.com'
    assert link in message.body
    assert 'SECRET_RAW_TOKEN' not in caplog.text


def test_task_retries_on_smtp_failure(db):
    """При сбое SMTP задача повторяется с backoff до max_retries и затем падает."""
    with mock.patch('accounts.tasks.send_mail', side_effect=RuntimeError('smtp down')) as send_mock:
        result = send_magic_link_email.apply(args=['user@example.com', 'https://example.com/link'])

    assert result.failed()
    # Первый вызов + max_retries повторов.
    assert send_mock.call_count == send_magic_link_email.max_retries + 1


def test_view_returns_200_and_dispatches_for_active_user(db, api_client, user, magic_link_request_url, caplog):
    """Для активного пользователя view отвечает 200, создаёт токен, ставит задачу один раз и не логирует токен."""
    with mock.patch('accounts.views.magic_link.send_magic_link_email.delay') as delay_mock:
        with caplog.at_level(logging.DEBUG, logger='accounts.views.magic_link'):
            response = api_client.post(magic_link_request_url, {'email': user.email}, format='json')

    assert response.status_code == 200
    assert MagicLinkToken.objects.filter(user=user).exists()
    delay_mock.assert_called_once()
    call_args = delay_mock.call_args.args
    assert call_args[0] == user.email
    link = call_args[1]
    assert '/auth/login/magic-link?token=' in link
    # The raw token/link must never reach the view's log stream (security regression guard).
    raw_token = link.split('token=', 1)[1]
    assert raw_token not in caplog.text
    assert link not in caplog.text


def test_view_returns_200_when_broker_unavailable(db, api_client, user, magic_link_request_url):
    """Если брокер недоступен и .delay падает, view всё равно отвечает 200 (анти-энумерация)."""
    with mock.patch(
        'accounts.views.magic_link.send_magic_link_email.delay',
        side_effect=RuntimeError('broker down'),
    ):
        response = api_client.post(magic_link_request_url, {'email': user.email}, format='json')

    assert response.status_code == 200
    assert MagicLinkToken.objects.filter(user=user).exists()


def test_view_returns_200_without_dispatch_for_unknown_email(db, api_client, magic_link_request_url):
    """Для неизвестного email view отвечает 200 и не ставит задачу в очередь."""
    with mock.patch('accounts.views.magic_link.send_magic_link_email.delay') as delay_mock:
        response = api_client.post(magic_link_request_url, {'email': 'nobody@example.com'}, format='json')

    assert response.status_code == 200
    delay_mock.assert_not_called()
    assert not MagicLinkToken.objects.exists()
