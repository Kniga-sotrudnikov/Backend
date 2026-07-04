from django.contrib import admin

from structure.models import Department, OrgStructureImage


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'short_name',
        'type',
        'parent',
        'head',
        'is_active',
    )
    search_fields = ('name', 'type', 'head__full_name')


@admin.register(OrgStructureImage)
class OrgStructureImageAdmin(admin.ModelAdmin):
    readonly_fields = ('updated_at',)
