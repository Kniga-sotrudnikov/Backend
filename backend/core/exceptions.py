from typing import Any

from rest_framework import exceptions as drf_exceptions
from rest_framework.views import exception_handler as drf_exception_handler

_CODE_OVERRIDES: dict[type[Exception], str] = {
    drf_exceptions.ValidationError: 'validation_error',
}


def _flat(value: Any) -> list[str]:
    """Рекурсивно разворачивает DRF-структуру ошибок в плоский список строк.

    Args:
        value: Любая DRF-структура ошибок — ``ErrorDetail``,
               ``list[ErrorDetail]`` или ``dict`` (вложенные сериализаторы).

    Returns:
        Плоский список строк с сообщениями об ошибках.
    """
    if isinstance(value, list):
        return [s for v in value for s in _flat(v)]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _flat(v)]
    return [str(value)]


def exception_handler(exc: Exception, context: dict) -> Any:
    """Кастомный обработчик исключений DRF (api-contract §1.7).

    Приводит все ошибки к единому формату::

        {'detail': 'Описание ошибки', 'code': 'error_code', 'field_errors': {'email': ['...'], 'phone': ['...']}}

    Логика ``detail``:

    - Если в ``data`` есть ключ ``detail`` (404, 403, 401) — берётся он.
    - Если есть ``non_field_errors`` — берётся первое сообщение из них.
    - Иначе — первое сообщение из ``field_errors``.

    Args:
        exc: Исключение, пойманное DRF.
        context: Контекст запроса (``view``, ``request`` и т.д.).

    Returns:
        ``Response`` с нормализованным телом ошибки,
        либо ``None`` если исключение не обработано DRF.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    code = _CODE_OVERRIDES.get(type(exc)) or getattr(exc, 'default_code', 'error')

    if not isinstance(data, dict):
        msgs = _flat(data)
        response.data = {
            'detail': msgs[0] if msgs else '',
            'code': code,
            'field_errors': {},
        }
        return response

    if 'detail' in data:
        detail = str(data['detail'])
    else:
        msgs = _flat(data.get('non_field_errors', [])) or _flat(data)
        detail = msgs[0] if msgs else ''

    field_errors = {k: _flat(v) for k, v in data.items() if k not in ('detail', 'non_field_errors')}

    response.data = {'detail': detail, 'code': code, 'field_errors': field_errors}
    return response
