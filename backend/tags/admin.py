from django.contrib import admin

from tags.models import EmployeeTag, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_or_icon')
    search_fields = ('name',)


@admin.register(EmployeeTag)
class EmployeeTagAdmin(admin.ModelAdmin):
    list_display = ('tag', 'employee', 'assigned_by', 'assigned_at')
    search_fields = ('tag__name', 'employee__full_name')
