import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser
from django.utils import timezone

from accounts.models import MagicLinkToken

_TOKEN_LIFETIME = 15


def generate_magic_token(user: AbstractBaseUser) -> str:
    """
    Генерирует одноразовый magic-link токен для пользователя.

    Args:
        user: Пользователь, для которого создаётся токен.

    Returns:
        Сырой magic-link токен.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    MagicLinkToken.objects.create(
        user=user, token_hash=token_hash, expires_at=timezone.now() + timedelta(minutes=_TOKEN_LIFETIME)
    )
    return raw_token


def get_token_instance(raw_token: str) -> MagicLinkToken | None:
    """
    Возвращает экземпляр MagicLinkToken по сырому токену.

    Args:
        raw_token: Сырой токен из magic-link ссылки.

    Returns:
        Экземпляр MagicLinkToken, если токен валиден,
        иначе None.
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = MagicLinkToken.objects.filter(token_hash=token_hash).select_related('user').first()
    if not token or not token.is_valid():
        return None
    return token
