from core.models import BaseModel, SoftDeleteModel
from django.conf import settings
from django.db import models
from employees.constants import (
    EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    JOB_TITLE_MAX_LENGTH,
    PHONE_MAX_LENGTH,
    STATUS_MAX_LENGTH,
)


class Status(models.TextChoices):
    """Статусы сотрудника."""

    ACTIVE = 'active', 'Активный'
    ARCHIVED = 'archived', 'Архивированный'


class Employee(BaseModel, SoftDeleteModel):
    """Карточка сотрудника организации."""

    full_name = models.CharField(
        max_length=FULL_NAME_MAX_LENGTH,
        verbose_name='Полное имя',
    )
    job_title = models.CharField(
        max_length=JOB_TITLE_MAX_LENGTH,
        verbose_name='Должность',
    )
    role_description = models.TextField(
        blank=True,
        verbose_name='Роль',
    )
    email = models.EmailField(
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
        verbose_name='Электронная почта',
    )
    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        blank=True,
        verbose_name='Телефон',
    )
    interests = models.TextField(
        blank=True,
        verbose_name='Компетенции',
    )
    birthday = models.DateField(
        verbose_name='День рождения',
    )
    status = models.CharField(
        max_length=STATUS_MAX_LENGTH,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='Статус',
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employee',
        verbose_name='Пользователь',
    )
    department = models.ForeignKey(
        'structure.Department',
        on_delete=models.PROTECT,
        limit_choices_to={'type': 'department'},
        related_name='employees',
        verbose_name='Отдел',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_employees',
        verbose_name='Кем создано',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_employees',
        verbose_name='Кем обновлено',
    )

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
        ordering = ('full_name',)

    def __str__(self):
        return self.full_name

    @property
    def direction(self):
        """Возвращает направление сотрудника на основе родителя отдела."""
        parent = self.department.parent
        if parent and parent.type == 'direction':
            return parent
        return None
