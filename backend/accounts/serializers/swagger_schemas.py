from rest_framework import serializers


class AuthUserResponseSerializer(serializers.Serializer):
    """Схема краткой информации о пользователе внутри токена."""

    id = serializers.IntegerField(help_text='ID пользователя')
    email = serializers.EmailField(help_text='Электронная почта')
    role = serializers.CharField(help_text='Роль: hr_admin|employee')
    employee_id = serializers.IntegerField(
        allow_null=True, help_text='ID связанной карточки сотрудника (null, если нет)'
    )


class TokenPairResponseSerializer(serializers.Serializer):
    """Схема успешного ответа аутентификации (200 OK)."""

    access = serializers.CharField(help_text='JWT access токен')
    refresh = serializers.CharField(help_text='JWT refresh токен')
    user = AuthUserResponseSerializer()


class AuthErrorResponseSerializer(serializers.Serializer):
    """Схема ответа при ошибке аутентификации (401 Unauthorized)."""

    detail = serializers.CharField(default='Активных учетных записей с указанными данными не найдено')
    code = serializers.CharField(default='authentication_failed')
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()), required=False, help_text='Ошибки валидации полей'
    )
