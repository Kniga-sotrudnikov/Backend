import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from employees.models import InaccuracyReport

logger = logging.getLogger(__name__)


@shared_task(name='notifications.tasks.ping')
def ping() -> str:
    """Smoke-таска. Вызов из shell: from notifications.tasks import ping; ping.delay()."""
    logger.info('pong')
    return 'pong'


@shared_task(name='notifications.tasks.notify_hr_about_inaccuracy_report')
def notify_hr_about_inaccuracy_report(report_id: int) -> dict:
    """Пишет в консоль email-уведомление HR о новом обращении."""
    try:
        report = InaccuracyReport.objects.select_related('employee', 'created_by').get(pk=report_id)
    except ObjectDoesNotExist:
        logger.warning('Отчет о неточностях {} не найден'.format(report_id))
        return {'sent': 0, 'reason': 'report_not_found'}

    user_model = get_user_model()
    hr_emails = list(user_model.objects.filter(role='hr_admin', is_active=True).values_list('email', flat=True))

    recipients = ', '.join(hr_emails) if hr_emails else 'активные HR не найдены'
    message = 'Обращение {} отправлено HR для сотрудника {} - {}. Получатели: {}'.format(
        report.id,
        report.employee_id,
        report.employee.full_name,
        recipients,
    )
    logger.info(message)
    return {'sent': len(hr_emails), 'report_id': report.id}
