from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024


def validate_file_extension(file):
    """Проверка расширения загружаемого фото."""
    ext = file.name.split('.')[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('Разрешены только JPEG, PNG и WebP')


def validate_file_size(file):
    """Проверка размера загружаемого фото."""
    if file.size > MAX_FILE_SIZE:
        raise ValidationError('Максимальный размер файла — 5MB')
