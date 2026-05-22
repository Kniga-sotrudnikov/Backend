from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from accounts.constants import MAX_LENGTH_FIRST_NAME, MAX_LENGTH_LAST_NAME, ROLE_MAX_LENGTH, TOKEN_HASH_MAX_LENGTH


class Role(models.TextChoices):
    """Роли пользователей."""

    HR_ADMIN = 'hr_admin', 'Эйчар админ'
    EMPLOYEE = 'employee', 'Сотрудник'


class User(AbstractUser):
    """Базовая модель пользователя наследуется от AbstractUser."""

    first_name = models.CharField(max_length=MAX_LENGTH_FIRST_NAME)
    last_name = models.CharField(max_length=MAX_LENGTH_LAST_NAME)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=ROLE_MAX_LENGTH, choices=Role.choices, verbose_name='Роль', default=Role.EMPLOYEE
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    @property
    def is_hr(self):
        """Проверяет является ли пользователь эйчаром."""
        return self.role == Role.HR_ADMIN

    @property
    def is_employee(self):
        """Проверяет является пользователь сотрудником."""
        return self.role == Role.EMPLOYEE

    def __str__(self):
        return self.email


class MagicLinkToken(models.Model):
    """Одноразовый токен для аутентификации пользователя через magic link."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='magic_tokens', verbose_name='Пользователь'
    )
    token_hash = models.CharField(max_length=TOKEN_HASH_MAX_LENGTH, unique=True, verbose_name='Хэш токена')
    expires_at = models.DateTimeField(verbose_name='Истекает')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='Использован')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()
