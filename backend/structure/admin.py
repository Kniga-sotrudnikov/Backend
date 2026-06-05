from django.contrib import admin

from structure.models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'short_name',
        'type',
        'parent',
        'is_active',
    )
    search_fields = ('name', 'type')
