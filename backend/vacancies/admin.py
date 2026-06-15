from django.contrib import admin
from vacancies.models import Vacancy


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'department',
        'status',
    )

    list_filter = (
        'status',
        'department',
    )

    search_fields = ('title',)
