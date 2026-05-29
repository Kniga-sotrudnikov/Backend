import os
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from employees.models import (
    PHOTO_MAX_WIDTH,
    THUMB_SIZE,
)

pytestmark = pytest.mark.django_db


def test_upload_success_and_thumbnail_generation(api_client, hr, employee_instance, upload_url, dummy_image_factory):
    """Успешная загрузка большого фото: пропорции оригинала и центр-кроп миниатюры."""
    api_client.force_authenticate(user=hr)

    # Генерируем картинку 1200x800 (больше лимита PHOTO_MAX_WIDTH)
    image_bytes = dummy_image_factory(width=1200, height=800)
    uploaded_file = SimpleUploadedFile('avatar.jpg', image_bytes, content_type='image/jpeg')

    response = api_client.post(upload_url, {'photo': uploaded_file}, format='multipart')

    assert response.status_code == status.HTTP_200_OK
    assert 'photo_url' in response.data

    employee_instance.refresh_from_db()
    assert employee_instance.photo
    assert employee_instance.photo_thumb

    # Проверяем пропорциональный ресайз оригинала до лимитов (с учетом погрешности округления высоты)
    with Image.open(employee_instance.photo.path) as orig_img:
        w, h = orig_img.size
        assert w == PHOTO_MAX_WIDTH
        assert h < PHOTO_MAX_WIDTH  # Картинка осталась альбомной

    # Проверяем создание квадратной миниатюры
    with Image.open(employee_instance.photo_thumb.path) as thumb_img:
        assert thumb_img.size == (THUMB_SIZE, THUMB_SIZE)


def test_upload_denied_for_large_file(api_client, hr, upload_url):
    """Отказ в загрузке, если файл превышает лимит в 5 МБ."""
    api_client.force_authenticate(user=hr)

    # Имитируем файл размером 6 МБ
    large_bytes = b'0' * (6 * 1024 * 1024)
    uploaded_file = SimpleUploadedFile('huge.jpg', large_bytes, content_type='image/jpeg')

    response = api_client.post(upload_url, {'photo': uploaded_file}, format='multipart')

    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE]


def test_upload_denied_for_invalid_extension(api_client, hr, upload_url):
    """Отказ в загрузке невалидного текстового формата вместо картинки."""
    api_client.force_authenticate(user=hr)

    txt_bytes = b'This is plain text, not an image.'
    uploaded_file = SimpleUploadedFile('document.txt', txt_bytes, content_type='text/plain')

    response = api_client.post(upload_url, {'photo': uploaded_file}, format='multipart')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_permission_denied_for_non_hr(api_client, user, upload_url, dummy_image_factory):
    """Проверка IsHR ограничений: обычный пользователь получает 403."""
    api_client.force_authenticate(user=user)

    image_bytes = dummy_image_factory()
    uploaded_file = SimpleUploadedFile('avatar.jpg', image_bytes, content_type='image/jpeg')

    response = api_client.post(upload_url, {'photo': uploaded_file}, format='multipart')
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_photo_replacement_removes_old_files_from_disk(
    api_client, hr, employee_instance, upload_url, dummy_image_factory
):
    """Замена фотографии успешно удаляет предыдущие оригиналы и миниатюры с диска."""
    api_client.force_authenticate(user=hr)

    # Шаг 1: Загружаем первое фото (размер 200x200)
    img1 = dummy_image_factory(200, 200)
    file1 = SimpleUploadedFile('first.jpg', img1, content_type='image/jpeg')
    api_client.post(upload_url, {'photo': file1}, format='multipart')

    employee_instance.refresh_from_db()
    old_photo_path = employee_instance.photo.path
    old_thumb_path = employee_instance.photo_thumb.path

    assert os.path.exists(old_photo_path)
    assert os.path.exists(old_thumb_path)

    # Шаг 2: Загружаем второе фото на замену (ВАЖНО: размер 350x350, чтобы хеш файла изменился!)
    img2 = dummy_image_factory(350, 350)
    file2 = SimpleUploadedFile('second.jpg', img2, content_type='image/jpeg')
    api_client.post(upload_url, {'photo': file2}, format='multipart')

    # Проверяем физическое удаление старых файлов из хранилища
    assert not os.path.exists(old_photo_path)
    assert not os.path.exists(old_thumb_path)
