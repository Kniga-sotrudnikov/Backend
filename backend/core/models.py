from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """Базовая абстрактная модель с полями времени создания и обновления."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """Менеджер по умолчанию: возвращает только не удалённые записи.

    ``Model.objects.all()`` автоматически исключает записи
    с ``is_deleted=True`` — без явного фильтра на стороне вызывающего кода.
    """

    def get_queryset(self) -> models.QuerySet:
        """Возвращает QuerySet, отфильтрованный по ``is_deleted=False``."""
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """Абстрактная модель с поддержкой мягкого удаления.

    Вместо физического удаления выставляет флаг ``is_deleted`` и фиксирует
    время удаления в ``deleted_at``.

    Менеджеры:
        objects:     активные записи (``is_deleted=False``).
        all_objects: все записи, включая удалённые.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = 'all_objects'

    def delete(self, using=None, keep_parents=False):
        """Мягкое удаление: выставляет флаг вместо физического удаления."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
