import io
import os
from importlib import reload
from urllib.parse import urlparse

import employeebook.urls as project_urls
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import clear_url_caches, reverse
from PIL import Image
from rest_framework import status

from structure.models import OrgStructureImage

pytestmark = pytest.mark.django_db

URL = reverse('org-structure-image')


def make_image_file(width=200, height=200, fmt='JPEG', name='chart.jpg', content_type='image/jpeg'):
    buf = io.BytesIO()
    Image.new('RGB', (width, height), color='red').save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=content_type)


# ---------------------------------------------------------------------------
# Права доступа
# ---------------------------------------------------------------------------


def test_get_requires_authentication(api_client):
    """GET без токена → 401."""
    response = api_client.get(URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_post_requires_authentication(api_client):
    """POST без токена → 401."""
    response = api_client.post(URL, {'image': make_image_file()}, format='multipart')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_patch_requires_authentication(api_client):
    """PATCH без токена → 401."""
    response = api_client.patch(URL, {'image': make_image_file()}, format='multipart')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_post_forbidden_for_non_hr(auth_client):
    """POST от обычного пользователя → 403."""
    response = auth_client.post(URL, {'image': make_image_file()}, format='multipart')
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_patch_forbidden_for_non_hr(auth_client):
    """PATCH от обычного пользователя → 403."""
    response = auth_client.patch(URL, {'image': make_image_file()}, format='multipart')
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


def test_get_returns_404_when_no_image(auth_client):
    """GET до первой загрузки → 404."""
    response = auth_client.get(URL)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_returns_200_after_upload(hr_client, dummy_image_factory):
    """GET после загрузки изображения → 200 с image_url и updated_at."""
    file = SimpleUploadedFile('chart.jpg', dummy_image_factory(), content_type='image/jpeg')
    hr_client.post(URL, {'image': file}, format='multipart')

    response = hr_client.get(URL)

    assert response.status_code == status.HTTP_200_OK
    assert 'image_url' in response.data
    assert 'updated_at' in response.data


def test_get_image_url_is_absolute(hr_client, dummy_image_factory):
    """image_url в ответе должен быть абсолютным URL."""
    file = SimpleUploadedFile('chart.jpg', dummy_image_factory(), content_type='image/jpeg')
    hr_client.post(URL, {'image': file}, format='multipart')

    response = hr_client.get(URL)

    assert response.data['image_url'].startswith('http')


def test_get_accessible_by_employee(api_client, user, hr_client, dummy_image_factory):
    """Обычный пользователь может получить изображение через GET."""
    file = SimpleUploadedFile('chart.jpg', dummy_image_factory(), content_type='image/jpeg')
    hr_client.post(URL, {'image': file}, format='multipart')

    api_client.force_authenticate(user=user)
    response = api_client.get(URL)

    assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------


def test_post_jpeg_returns_201(hr_client):
    """POST с JPEG → 201, image_url в ответе."""
    response = hr_client.post(URL, {'image': make_image_file()}, format='multipart')

    assert response.status_code == status.HTTP_201_CREATED
    assert 'image_url' in response.data


def test_post_png_returns_201(hr_client):
    """POST с PNG → 201."""
    file = make_image_file(fmt='PNG', name='chart.png', content_type='image/png')
    response = hr_client.post(URL, {'image': file}, format='multipart')

    assert response.status_code == status.HTTP_201_CREATED


def test_post_creates_db_record(hr_client, dummy_image_factory):
    """После POST в БД ровно одна запись OrgStructureImage."""
    file = SimpleUploadedFile('chart.jpg', dummy_image_factory(), content_type='image/jpeg')
    hr_client.post(URL, {'image': file}, format='multipart')

    assert OrgStructureImage.objects.count() == 1


def test_post_returns_absolute_url(hr_client, dummy_image_factory):
    """POST возвращает абсолютный image_url."""
    file = SimpleUploadedFile('chart.jpg', dummy_image_factory(), content_type='image/jpeg')
    response = hr_client.post(URL, {'image': file}, format='multipart')

    assert response.data['image_url'].startswith('http')


def test_double_post_keeps_singleton(hr_client, dummy_image_factory):
    """Два последовательных POST → в БД по-прежнему одна запись (singleton)."""
    hr_client.post(
        URL,
        {'image': SimpleUploadedFile('a.jpg', dummy_image_factory(200, 200), content_type='image/jpeg')},
        format='multipart',
    )
    hr_client.post(
        URL,
        {'image': SimpleUploadedFile('b.jpg', dummy_image_factory(300, 300), content_type='image/jpeg')},
        format='multipart',
    )

    assert OrgStructureImage.objects.count() == 1


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------


def test_patch_returns_200(hr_client, dummy_image_factory):
    """PATCH после первичной загрузки → 200 с новым image_url."""
    hr_client.post(
        URL,
        {'image': SimpleUploadedFile('first.jpg', dummy_image_factory(200, 200), content_type='image/jpeg')},
        format='multipart',
    )

    response = hr_client.patch(
        URL,
        {'image': SimpleUploadedFile('second.jpg', dummy_image_factory(300, 300), content_type='image/jpeg')},
        format='multipart',
    )

    assert response.status_code == status.HTTP_200_OK
    assert 'image_url' in response.data


def test_patch_replaces_image_url(hr_client, dummy_image_factory):
    """После PATCH image_url отличается от предыдущего (новый хэш файла)."""
    hr_client.post(
        URL,
        {'image': SimpleUploadedFile('first.jpg', dummy_image_factory(200, 200), content_type='image/jpeg')},
        format='multipart',
    )
    first_url = hr_client.get(URL).data['image_url']

    hr_client.patch(
        URL,
        {'image': SimpleUploadedFile('second.jpg', dummy_image_factory(300, 300), content_type='image/jpeg')},
        format='multipart',
    )
    second_url = hr_client.get(URL).data['image_url']

    assert first_url != second_url


def test_patch_deletes_old_file_from_disk(hr_client, dummy_image_factory):
    """При замене через PATCH старый файл удаляется из хранилища."""
    hr_client.post(
        URL,
        {'image': SimpleUploadedFile('first.jpg', dummy_image_factory(200, 200), content_type='image/jpeg')},
        format='multipart',
    )
    old_path = OrgStructureImage.objects.get(pk=1).image.path

    hr_client.patch(
        URL,
        {'image': SimpleUploadedFile('second.jpg', dummy_image_factory(300, 300), content_type='image/jpeg')},
        format='multipart',
    )

    assert not os.path.exists(old_path)


# ---------------------------------------------------------------------------
# Валидация
# ---------------------------------------------------------------------------


def test_post_rejects_webp(hr_client):
    """WebP запрещён — только JPEG и PNG."""
    file = make_image_file(fmt='WEBP', name='chart.webp', content_type='image/webp')
    response = hr_client.post(URL, {'image': file}, format='multipart')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_rejects_oversized_file(hr_client):
    """Файл более 5 МБ → 400."""
    large_bytes = b'0' * (6 * 1024 * 1024)
    file = SimpleUploadedFile('big.jpg', large_bytes, content_type='image/jpeg')
    response = hr_client.post(URL, {'image': file}, format='multipart')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_rejects_non_image_file(hr_client):
    """Текстовый файл вместо изображения → 400."""
    file = SimpleUploadedFile('doc.txt', b'not an image', content_type='text/plain')
    response = hr_client.post(URL, {'image': file}, format='multipart')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_rejects_missing_image_field(hr_client):
    """POST без поля image → 400."""
    response = hr_client.post(URL, {}, format='multipart')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Доступность по URL (dev-режим)
# ---------------------------------------------------------------------------


@override_settings(DEBUG=True)
def test_uploaded_image_accessible_by_media_url(hr_client, dummy_image_factory):
    """Загруженный файл должен отдаваться по image_url в dev-режиме."""
    clear_url_caches()
    reload(project_urls)

    try:
        file = SimpleUploadedFile('chart.jpg', dummy_image_factory(200, 200), content_type='image/jpeg')
        post_response = hr_client.post(URL, {'image': file}, format='multipart')

        assert post_response.status_code == status.HTTP_201_CREATED
        media_path = urlparse(post_response.data['image_url']).path
        media_response = hr_client.get(media_path)

        assert media_response.status_code == status.HTTP_200_OK
    finally:
        clear_url_caches()
        reload(project_urls)
