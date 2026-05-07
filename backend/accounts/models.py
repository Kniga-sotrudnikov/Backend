from django.contrib.auth.models import AbstractUser
from django.db import models

from accounts.constants import ROLE_MAX_LENGTH


class Role(models.TextChoices):
    """Роли пользователей."""

    HR_ADMIN = 'hr_admin', 'Эйчар админ'
    EMPLOYEE = 'employee', 'Сотрудник'


class User(AbstractUser):
    """Базовая модель пользователя наследуется от AbstractUser."""

    role = models.CharField(max_length=ROLE_MAX_LENGTH, choices=Role.choices, verbose_name='Роль')

    def __str__(self):
        return self.username
