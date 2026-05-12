from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.serializers.token_obtain import EmailTokenObtainPairSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    """Вход по Email/Password."""

    serializer_class = EmailTokenObtainPairSerializer
