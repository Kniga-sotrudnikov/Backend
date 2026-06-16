import logging

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from notifications.models import BirthdayLog, BirthdayNotificationSettings

from employees.models import Employee
from employees.utils import get_birthday_days_condition

logger = logging.getLogger(__name__)


@shared_task(name='notifications.tasks.ping')
def ping() -> str:
    """Smoke-таска. Вызов из shell: from notifications.tasks import ping; ping.delay()."""
    logger.info('pong')
    return 'pong'


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
