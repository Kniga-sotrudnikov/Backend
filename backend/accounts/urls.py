from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views.magic_link import MagicLinkRequestView, MagicLinkVerifyView
from core.constants import ANY_ROLE, AUTH_TAG

urlpatterns = [
    path(
        'auth/login/',
        extend_schema(tags=[AUTH_TAG], summary='Получение токена по email/паролю', description=ANY_ROLE)(
            TokenObtainPairView
        ).as_view(),
        name='token_obtain',
    ),
    path(
        'auth/token/refresh/',
        extend_schema(tags=[AUTH_TAG], summary='Обновление токена', description=ANY_ROLE)(TokenRefreshView).as_view(),
        name='token_refresh',
    ),
    path('auth/login/magic-link/', MagicLinkRequestView.as_view(), name='magic_link'),
    path('auth/login/magic-link/verify/', MagicLinkVerifyView.as_view()),
]
