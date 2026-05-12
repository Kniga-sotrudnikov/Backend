import hashlib
import os
import uuid

from django.core.files.storage import FileSystemStorage


class HashedFileStorage(FileSystemStorage):
    """Кастомное хранилище с автоматическим переименованием файлов в уникальные хэши."""

    def generate_filename(self, filename):

        extension = os.path.splitext(filename)[1].lower()
        unique_string = uuid.uuid4().hex
        file_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:32]
        dirname = os.path.dirname(filename)

        return os.path.join(dirname, f'{file_hash}{extension}')
