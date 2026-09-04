import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'employeebook.settings')

app = Celery('employeebook')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-birthdays-every-day': {
        'task': 'notifications.tasks.check_upcoming_birthdays',
        'schedule': crontab(hour=9, minute=0),
    },
}
