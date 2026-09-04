import logging

from celery import shared_task
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    name='accounts.tasks.send_magic_link_email',
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_magic_link_email(email: str, link: str) -> None:
    """Отправляет письмо с одноразовой magic-link ссылкой.

    Выполняется в Celery-воркере, чтобы SMTP-доставка не блокировала
    HTTP-запрос. При транзиентных ошибках задача повторяется с
    экспоненциальной задержкой до 3 раз.

    Args:
        email: Адрес получателя.
        link: Одноразовая magic-link ссылка для входа.
    """
    subject = 'Ссылка для входа'
    message = (
        'Здравствуйте!\n\n'
        'Вы запросили ссылку для входа. Перейдите по ссылке ниже, '
        'чтобы войти в систему:\n\n'
        f'{link}\n\n'
        'Ссылка одноразовая и действует ограниченное время. '
        'Если вы не запрашивали вход, просто проигнорируйте это письмо.\n'
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
    logger.info('Magic link email sent')
