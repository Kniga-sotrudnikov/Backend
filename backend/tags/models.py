from django.contrib.auth import get_user_model
from django.db import models
from django.utils.timezone import now

User = get_user_model()


class Tag(models.Model):
    """Модель для тегов."""

    name = models.CharField(
        verbose_name='Название тега', max_length=100, unique=True, help_text='Название тега должно быть уникальным.'
    )
    color_or_icon = models.CharField(
        verbose_name='Цвет или иконка',
        max_length=50,
        blank=True,
        help_text=('Цветовое обозначение (например, #FF0000)или идентификатор значка.'),
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class EmployeeTag(models.Model):
    """
    Связующая модель для назначения тегов сотрудникам.

    Используется для хранения аудиторской информации.
    """

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='employee_tags', verbose_name='Тег')
    employee = models.ForeignKey(
        'employees.Employee', on_delete=models.CASCADE, related_name='employee_tags', verbose_name=('Сотрудник')
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_employee_tags',
        verbose_name='Кем назначен тег',
    )
    assigned_at = models.DateTimeField(
        verbose_name='Когда назначен тег', default=now, help_text='Дата и время присвоения тега.'
    )

    class Meta:
        verbose_name = 'Тег сотрудника'
        verbose_name_plural = 'Теги сотрудника'
        constraints = [
            models.UniqueConstraint(fields=['tag', 'employee'], name='unique_tag_employee'),
        ]
        ordering = ['-assigned_at']

    def __str__(self):
        return f'{self.employee.full_name} - {self.tag.name}'
