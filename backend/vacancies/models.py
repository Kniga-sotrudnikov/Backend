from django.db import models

from core.models import BaseModel, SoftDeleteModel
from structure.models import Department


class Vacancy(BaseModel, SoftDeleteModel):
    """Модель вакансии."""

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'

    title = models.CharField(max_length=255)

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='vacancies',
    )

    description = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    def __str__(self):
        return self.title
