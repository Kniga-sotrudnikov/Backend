from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers.magic_link import MagicLinkRequestSerializer, MagicLinkVerifySerializer
from accounts.service import generate_magic_token, get_token_instance

User = get_user_model()


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
            link = f'http://localhost:8000/auth/login/magic-link?token={raw_token}'
            print(f'Magic link: {link}')
        return Response({'detail': 'Ссылка отправлена на указанную почту'}, status=status.HTTP_200_OK)


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
            }
        )
