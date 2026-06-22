from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ORG_IMAGE_ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024


def validate_file_extension(file):
    """Проверка расширения загружаемого фото."""
    ext = file.name.split('.')[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('Разрешены только JPEG, PNG и WebP')


def validate_org_image_extension(file):
    """Проверка расширения изображения оргструктуры."""
    ext = file.name.split('.')[-1].lower()

    if ext not in ORG_IMAGE_ALLOWED_EXTENSIONS:
        raise ValidationError('Разрешены только JPEG и PNG')


def validate_file_size(file):
    """Проверка размера загружаемого фото."""
    if file.size > MAX_FILE_SIZE:
        raise ValidationError('Максимальный размер файла — 5MB')
