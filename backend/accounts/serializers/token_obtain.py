from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Сериализатор для входа по Email/Password с расширенным ответом."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
            'employee_id': getattr(self.user, 'employee', None) and self.user.employee.id,
        }
        return data
