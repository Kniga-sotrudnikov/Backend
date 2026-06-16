from django.contrib.auth import get_user_model
from django.db import models

from employees.models import Employee

User = get_user_model()


class Favorite(models.Model):
    """Модель избранного."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='favorited_by')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'employee'], name='unique_favorite')]
        ordering = ('-created_at',)

    def __str__(self):
        return f'избранный {self.employee} пользователя: {self.user}'
