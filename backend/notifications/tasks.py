import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.utils import timezone
from notifications.models import BirthdayLog, BirthdayNotificationSettings

from employees.models import Employee, InaccuracyReport
from employees.utils import get_birthday_days_condition

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


@shared_task(name='notifications.tasks.check_upcoming_birthdays')
def check_upcoming_birthdays() -> str:
    """Ежедневная таска для проверки ДР и уведомления HR."""
    settings = BirthdayNotificationSettings.load()

    if not settings.email_enabled or not settings.recipients:
        logger.info('Birthday notifications are disabled or recipients list is empty.')
        return 'Уведомления отключены или список получателей пуст.'

    today = timezone.now().date()
    current_year = today.year

    pairs = get_birthday_days_condition(settings.days_before)
    target_pair = pairs[-1] if pairs else (today.month, today.day)

    queryset = Employee.objects.filter(status='active', is_deleted=False)
    upcoming_birthdays = []

    for emp in queryset:
        if emp.birthday and (emp.birthday.month, emp.birthday.day) == target_pair:
            upcoming_birthdays.append(emp)

    sent_count = 0

    for employee in upcoming_birthdays:
        if BirthdayLog.objects.filter(employee=employee, year=current_year).exists():
            continue

        subject = f'Напоминание: Скоро день рождения сотрудника {employee.full_name}'
        message = (
            f'Уважаемый HR!\n\n'
            f'У сотрудника {employee.full_name} через {settings.days_before} дн. '
            f'будет день рождения ({employee.birthday.strftime("%d.%m")}).\n'
            f'Отдел: {employee.department.name if employee.department else "Не указан"}\n'
        )

        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@employeebook.ru',
            recipient_list=settings.recipients,
            fail_silently=False,
        )

        BirthdayLog.objects.create(employee=employee, year=current_year)
        sent_count += 1

    logger.info(f'Birthday notifications sent: {sent_count}')
    return f'Успешно отправлено уведомлений: {sent_count}'
