from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from accounts.views.magic_link import MagicLinkRequestView, MagicLinkVerifyView
from accounts.views.token_obtain import EmailTokenObtainPairView

urlpatterns = [
    path('auth/login/', EmailTokenObtainPairView.as_view()),
    path('auth/token/refresh/', TokenRefreshView.as_view()),
    path('auth/login/magic-link/', MagicLinkRequestView.as_view()),
    path(
        'auth/login/magic-link/verify/',
        MagicLinkVerifyView.as_view(),
    ),
]
