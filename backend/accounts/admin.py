from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    list_display = (
        'email',
        'first_name',
        'last_name',
        'role',
        'is_active',
    )
    search_fields = ('email',)
