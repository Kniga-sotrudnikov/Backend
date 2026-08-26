import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers.magic_link import MagicLinkRequestSerializer, MagicLinkVerifySerializer
from accounts.service import generate_magic_token, get_token_instance
from accounts.tasks import send_magic_link_email

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Аутентификация'],
    summary='Запрос магической ссылки',
    description='Доступно всем (без авторизации). Отправляет одноразовую ссылку на указанный email.',
)
class MagicLinkRequestView(GenericAPIView):
    serializer_class = MagicLinkRequestSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            raw_token = generate_magic_token(user)
            try:
                # CORS_ALLOWED_ORIGINS (not CSRF_TRUSTED_ORIGINS) holds the frontend's
                # own origin, which is where the SPA route that consumes the token
                # lives; in production it happens to match CSRF_TRUSTED_ORIGINS because
                # Caddy serves both frontend and API from the same domain.
                base_url = settings.CORS_ALLOWED_ORIGINS[0].rstrip('/')
                link = f'{base_url}/auth/login/magic-link?token={raw_token}'
                send_magic_link_email.delay(user.email, link)
            except Exception:
                # Never leak account existence: a broker outage or misconfigured
                # CORS_ALLOWED_ORIGINS must not turn the user-exists branch into a
                # 500 while the miss branch stays 200.
                logger.exception('Failed to enqueue magic link email for user %s', user.pk)
            logger.info('Magic link generated for user %s', user.pk)
        else:
            # Always answers 200 to avoid email enumeration, so the miss is only visible here.
            logger.info('Magic link requested for an unknown or inactive account')
        return Response({'detail': 'Ссылка отправлена на указанную почту'}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Аутентификация'],
    summary='Верификация магической ссылки',
    description='Доступно всем (без авторизации). Возвращает JWT access/refresh токены.',
)
class MagicLinkVerifyView(GenericAPIView):
    serializer_class = MagicLinkVerifySerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data['token']
        token = get_token_instance(raw_token)
        if not token:
            return Response({'detail': 'Неверный или истекший токен'}, status=status.HTTP_400_BAD_REQUEST)
        token.used_at = timezone.now()
        token.save(update_fields=['used_at'])
        refresh = RefreshToken.for_user(token.user)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': token.user.id,
                    'email': token.user.email,
                    'role': token.user.role,
                    'employee_id': getattr(token.user, 'employee', None) and token.user.employee.id,
                },
            }
        )
