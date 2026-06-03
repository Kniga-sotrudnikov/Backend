import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='notifications.tasks.ping')
def ping() -> str:
    """Smoke-таска. Вызов из shell: from notifications.tasks import ping; ping.delay()."""
    logger.info('pong')
    return 'pong'
