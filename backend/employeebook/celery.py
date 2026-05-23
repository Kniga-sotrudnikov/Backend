import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'employeebook.settings')

app = Celery('employeebook')

app.config_from_object('django.conf:settings', namespace='CELERY')
