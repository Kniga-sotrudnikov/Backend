from django.contrib import admin
from employees.models import Employee

from tags.models import EmployeeTag


class EmployeeTagInline(admin.TabularInline):
    model = EmployeeTag
    extra = 1


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'job_title', 'department', 'status')
    list_filter = ('status', 'department__type', 'department')
    search_fields = ('full_name', 'email', 'job_title')
    autocomplete_fields = ('department', 'user')
    inlines = (EmployeeTagInline,)
    actions = ('archive_all',)

    @admin.action(description='массово архивировать')
    def archive_all(self, request, queryset):
        archived = queryset.update(status='archived')
        self.message_user(request, f'Архивировано {archived}')
