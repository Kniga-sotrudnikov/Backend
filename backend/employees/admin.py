from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from employees.models import Employee, InaccuracyReport, InaccuracyReportStatus
from employees.services import archive_employee
from structure.models import Department
from tags.models import EmployeeTag, Tag


class EmployeeTagInline(admin.TabularInline):
    model = EmployeeTag
    fields = ('tag',)
    autocomplete_fields = ('tag',)
    extra = 1


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    add_fieldsets = (
        (
            'Основные данные сотрудника',
            {
                'fields': (
                    'full_name',
                    'job_title',
                    'email',
                    'birthday',
                    'department',
                ),
            },
        ),
        (
            'Контакты',
            {
                'fields': (
                    'phone',
                    'city',
                ),
            },
        ),
    )
    fieldsets = (
        (
            'Основные данные сотрудника',
            {
                'fields': (
                    'full_name',
                    'job_title',
                    'email',
                    'birthday',
                    'department',
                    'status',
                ),
            },
        ),
        (
            'Контакты',
            {
                'fields': (
                    'phone',
                    'city',
                    'personal_phone',
                    'personal_email',
                ),
            },
        ),
        (
            'Профиль сотрудника',
            {
                'fields': (
                    'photo',
                    'role_description',
                    'interests',
                    'employment_status',
                    'crm_profile',
                    'social_network',
                    'resume_link',
                ),
            },
        ),
        (
            'Руководитель',
            {
                'fields': (
                    'supervisor',
                    'supervisor_role',
                    'supervisor_photo',
                ),
            },
        ),
        (
            'Доступ к системе',
            {
                'fields': ('user',),
            },
        ),
    )
    list_display = (
        'full_name',
        'job_title',
        'department',
        'city',
        'employment_status',
        'status',
        'supervisor',
        'email',
        'phone',
    )
    list_filter = (
        'status',
        'employment_status',
        'department__type',
        'department',
        'city',
    )
    search_fields = (
        'full_name',
        'email',
        'phone',
        'personal_phone',
        'personal_email',
        'city',
        'job_title',
    )
    autocomplete_fields = ('department', 'user', 'supervisor', 'supervisor_role', 'supervisor_photo')
    inlines = (EmployeeTagInline,)
    actions = ('archive_all', 'change_department_action', 'assign_tag_action')

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Добавить сотрудника'
        return super().add_view(request, form_url, extra_context)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_inlines(self, request, obj):
        if obj is None:
            return ()
        return super().get_inlines(request, obj)

    def save_model(self, request, obj, form, change):
        if change:
            obj.updated_by = request.user
        elif obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='массово архивировать')
    def archive_all(self, request, queryset):
        employees = list(queryset)
        for employee in employees:
            archive_employee(employee=employee, updated_by=request.user)
        self.message_user(request, f'Архивировано {len(employees)}')

    @admin.action(description='массово сменить отдел')
    def change_department_action(self, request, queryset):
        if 'apply' in request.POST:
            department = Department.objects.get(pk=request.POST['department'])
            employees = list(queryset)
            for employee in employees:
                employee.department = department
                employee.updated_by = request.user
                employee.save(update_fields=['department', 'updated_by'])
            self.message_user(request, f'Отдел изменён для {len(employees)} сотрудников')
            changelist_url = reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist')
            return HttpResponseRedirect(changelist_url)
        departments = Department.objects.filter(is_active=True, type=Department.Type.DEPARTMENT)
        return render(
            request,
            'admin/employees/change_department.html',
            {
                'queryset': queryset,
                'departments': departments,
                **self.admin_site.each_context(request),
            },
        )

    @admin.action(description='массово назначить тег')
    def assign_tag_action(self, request, queryset):
        if 'apply' in request.POST:
            tag = Tag.objects.get(pk=request.POST['tag'])
            EmployeeTag.objects.bulk_create(
                [EmployeeTag(tag=tag, employee=employee, assigned_by=request.user) for employee in queryset],
                ignore_conflicts=True,
            )
            self.message_user(request, f'Тег «{tag}» назначен сотрудникам')
            changelist_url = reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist')
            return HttpResponseRedirect(changelist_url)
        tags = Tag.objects.all()
        return render(
            request,
            'admin/employees/assign_tag.html',
            {
                'queryset': queryset,
                'tags': tags,
                **self.admin_site.each_context(request),
            },
        )


@admin.register(InaccuracyReport)
class InaccuracyReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'employee')
    search_fields = ('employee__full_name', 'message', 'created_by__email')
    readonly_fields = ('employee', 'message', 'created_by', 'created_at')
    autocomplete_fields = ('employee',)
    actions = ('mark_as_resolved',)

    @admin.action(description='пометить решённым')
    def mark_as_resolved(self, request, queryset):
        updated_count = queryset.update(status=InaccuracyReportStatus.RESOLVED)
        self.message_user(request, f'Помечено решёнными: {updated_count}')
