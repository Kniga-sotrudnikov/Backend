from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models


class BirthdayNotificationSettings(models.Model):
    email_enabled = models.BooleanField(default=True, verbose_name='Включить уведомления')
    days_before = models.PositiveIntegerField(default=1, verbose_name='За сколько дней уведомлять')
    recipients = ArrayField(models.EmailField(), default=list, blank=True, verbose_name='Список Email получателей')

    class Meta:
        verbose_name = 'Настройки уведомлений о ДР'
        verbose_name_plural = 'Настройки уведомлений о ДР'

    def clean(self):
        # Гарантируем, что запись всегда будет только одна (синглтон)
        if BirthdayNotificationSettings.objects.exists() and not self.pk:
            raise ValidationError('Можно создать только один экземпляр настроек.')

    def save(self, *args, **kwargs):
        self.pk = 1  # Всегда сохраняем под id=1
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        # Метод для удобного получения настроек в Celery-таске
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BirthdayLog(models.Model):
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='birthday_logs')
    year = models.PositiveIntegerField(verbose_name='Год поздравления')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'year')  # Идемпотентность на уровне базы данных
        verbose_name = 'Лог отправки поздравлений'
        verbose_name_plural = 'Логи отправки поздравлений'

    def __str__(self):
        return f'ДР {self.employee} в {self.year} году'
