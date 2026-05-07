from http import HTTPStatus

from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """
    Кастомный обработчик исключений для DRF.

    Приводит все ошибки к единому формату:
    {
        "error": "Not Found",
        "detail": "Запрашиваемый объект не найден.",
        "status_code": 404
    }

    Если исключение не обработано DRF — возвращает None (стандартное поведение).
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        response.data = {
            'error': HTTPStatus(response.status_code).phrase,
            'detail': response.data,
            'status_code': response.status_code,
        }

    return response
