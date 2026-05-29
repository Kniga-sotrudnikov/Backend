import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from employees.constants import (
    EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    JOB_TITLE_MAX_LENGTH,
    PHONE_MAX_LENGTH,
    PHOTO_MAX_HEIGHT,
    PHOTO_MAX_WIDTH,
    PHOTO_QUALITY,
    STATUS_MAX_LENGTH,
    THUMB_QUALITY,
    THUMB_SIZE,
)
from medias.validators import validate_file_extension, validate_file_size
from PIL import Image

from core.models import BaseModel, SoftDeleteModel
from core.storage import HashedFileStorage
from structure.models import Department


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
    photo = models.ImageField(
        storage=HashedFileStorage(),
        upload_to='photos/originals/',
        blank=True,
        null=True,
        validators=(
            validate_file_extension,
            validate_file_size,
        ),
        verbose_name='Оригинальное фото',
    )
    photo_thumb = models.ImageField(
        storage=HashedFileStorage(),
        upload_to='photos/thumbs/',
        blank=True,
        null=True,
        editable=False,
        verbose_name='Миниатюра',
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
    def direction(self) -> Department | None:
        """Возвращает направление сотрудника на основе родителя отдела."""
        parent: Department = self.department.parent
        if parent and parent.type == Department.Type.DIRECTION:
            return parent
        return None

    def save(self, *args, **kwargs):
        """Сохраняет модель с оптимизированной обработкой изображений."""
        update_fields = kwargs.get('update_fields')

        # Если это мягкое удаление или обновление полей, не связанных с фото — выходим.
        if update_fields is not None and not set(update_fields).intersection({'photo', 'photo_thumb'}):
            super().save(*args, **kwargs)
            return

        # Если фото удалили (очистили поле) — чистим миниатюру и выходим.
        if not self.photo:
            self._clear_thumbnail(update_fields, kwargs)
            super().save(*args, **kwargs)
            return

        # Проверяем, изменилось ли фото.
        if not self._is_photo_changed():
            super().save(*args, **kwargs)
            return

        self._process_and_setup_images(update_fields, kwargs)
        super().save(*args, **kwargs)

    def _is_photo_changed(self) -> bool:
        """Проверяет, загружено ли новое фото по сравнению с БД."""
        if not self.pk:
            return True
        old_photo = Employee.all_objects.filter(pk=self.pk).values_list('photo', flat=True).first()
        return old_photo != self.photo.name

    def _clear_thumbnail(self, update_fields, kwargs):
        """Очищает поле миниатюры и удаляет файл из хранилища."""
        if self.photo_thumb:
            self.photo_thumb.delete(save=False)
            if update_fields is not None:
                kwargs['update_fields'] = list(set(update_fields).union({'photo_thumb'}))

    def _process_and_setup_images(self, update_fields, kwargs):
        """Оркестратор обработки оригинального фото и генерации миниатюры."""
        # Удаляем старую миниатюру перед генерацией новой
        if self.photo_thumb:
            self.photo_thumb.delete(save=False)

        # Читаем исходный файл один раз в память
        file_bytes = self.photo.read()
        filename = os.path.basename(self.photo.name)

        # 1. Обработка оригинала (макс PHOTO_MAX_WIDTH x PHOTO_MAX_HEIGHT, без апскейла)
        img_orig = Image.open(BytesIO(file_bytes)).convert('RGB')
        w_orig, h_orig = img_orig.size

        # Если картинка превышает рамки хотя бы по одной стороне — уменьшаем с сохранением пропорций
        if w_orig > PHOTO_MAX_WIDTH or h_orig > PHOTO_MAX_HEIGHT:
            img_orig.thumbnail((PHOTO_MAX_WIDTH, PHOTO_MAX_HEIGHT), Image.Resampling.LANCZOS)

        orig_io = BytesIO()
        img_orig.save(orig_io, format='JPEG', quality=PHOTO_QUALITY, optimize=True)
        self.photo.save(filename, ContentFile(orig_io.getvalue()), save=False)

        # 2. Создание квадратной миниатюры (THUMB_SIZE x THUMB_SIZE, центр-кроп)
        img_thumb = Image.open(BytesIO(file_bytes)).convert('RGB')
        w_thumb, h_thumb = img_thumb.size
        min_edge = min(w_thumb, h_thumb)

        # Центрирование рамки для кропа
        left = (w_thumb - min_edge) // 2
        top = (h_thumb - min_edge) // 2

        img_thumb = img_thumb.crop((left, top, left + min_edge, top + min_edge))
        img_thumb = img_thumb.resize((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)

        thumb_io = BytesIO()
        img_thumb.save(thumb_io, format='JPEG', quality=THUMB_QUALITY, optimize=True)
        self.photo_thumb = ContentFile(thumb_io.getvalue(), name=filename)

        # Синхронизируем update_fields, если они были переданы
        if update_fields is not None:
            kwargs['update_fields'] = list(set(update_fields).union({'photo', 'photo_thumb'}))
