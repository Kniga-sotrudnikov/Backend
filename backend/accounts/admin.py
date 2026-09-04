from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'username',
                    'first_name',
                    'last_name',
                    'role',
                    'usable_password',
                    'password1',
                    'password2',
                ),
            },
        ),
    )
    list_display = (
        'email',
        'first_name',
        'last_name',
        'role',
        'is_active',
    )
    search_fields = ('email',)
    fieldsets = UserAdmin.fieldsets + (('Роль', {'fields': ('role',)}),)
