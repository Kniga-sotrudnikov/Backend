from django.conf import settings
from django.db import models

from core.models import BaseModel, SoftDeleteModel


class Department(BaseModel, SoftDeleteModel):
    """
    Модель подразделения компании.

    Поддерживает иерархию (направления и отделы), мягкое удаление
    и аудит изменений.
    """

    # Константы для полей (пока здесь, потом - в отдельном файле с константами проекта)
    NAME_MAX_LENGTH = 255
    SHORT_NAME_MAX_LENGTH = 50
    TYPE_MAX_LENGTH = 20
    DEFAULT_DISPLAY_ORDER = 0

    class Type(models.TextChoices):
        """Типы подразделений: Направление (верхний уровень) или Отдел."""

        DIRECTION = 'direction', 'Направление'
        DEPARTMENT = 'department', 'Отдел'

    name = models.CharField(
        max_length=NAME_MAX_LENGTH, verbose_name='Название', help_text='Уникально в рамках родительского подразделения'
    )

    short_name = models.CharField(
        max_length=SHORT_NAME_MAX_LENGTH, null=True, blank=True, verbose_name='Сокращенное название'
    )

    description = models.TextField(null=True, blank=True, verbose_name='Описание')

    type = models.CharField(
        max_length=TYPE_MAX_LENGTH, choices=Type.choices, default=Type.DEPARTMENT, verbose_name='Тип'
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительское подразделение',
    )

    display_order = models.IntegerField(default=DEFAULT_DISPLAY_ORDER, verbose_name='Порядок отображения')

    is_active = models.BooleanField(default=True, verbose_name='Активен')

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_departments',
        verbose_name='Кем обновлено',
    )

    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_departments',
        verbose_name='Кем удалено',
    )

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'
        ordering = ('display_order', 'name')
        constraints = (models.UniqueConstraint(fields=('parent', 'name'), name='unique_name_per_parent'),)

    def __str__(self):
        return self.name
