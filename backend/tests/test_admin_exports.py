from io import BytesIO
from zipfile import ZipFile

import pytest
from django.urls import reverse
from vacancies.models import Vacancy

from employees.models import Status
from structure.models import Department

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _sheet_xml(response) -> str:
    with ZipFile(BytesIO(response.content)) as archive:
        return archive.read('xl/worksheets/sheet1.xml').decode()


@pytest.mark.django_db
def test_admin_employee_export_returns_filtered_xlsx(hr_client, employee_record):
    """Экспорт сотрудников возвращает XLSX с учётом фильтров списка."""
    department = Department.objects.create(
        name='Backend',
        type=Department.Type.DEPARTMENT,
    )
    employee_record(
        full_name='Иван Иванов',
        job_title='Backend Developer',
        email='ivan-export@example.com',
        department=department,
        status=Status.ACTIVE,
    )
    employee_record(
        full_name='Мария Петрова',
        job_title='HR Manager',
        email='maria-export@example.com',
        department=department,
        status=Status.ACTIVE,
    )

    response = hr_client.get(reverse('admin-employee-export'), data={'search': 'Иван'})

    assert response.status_code == 200
    assert response['Content-Type'] == XLSX_CONTENT_TYPE
    assert response['Content-Disposition'] == 'attachment; filename="employees.xlsx"'
    sheet_xml = _sheet_xml(response)
    assert 'Иван Иванов' in sheet_xml
    assert 'ivan-export@example.com' in sheet_xml
    assert 'Мария Петрова' not in sheet_xml


@pytest.mark.django_db
def test_admin_vacancy_export_returns_filtered_xlsx(hr_client, department):
    """Экспорт вакансий возвращает XLSX с учётом фильтра статуса."""
    Vacancy.objects.create(
        title='Backend Developer',
        department=department,
        description='Python',
        status=Vacancy.Status.OPEN,
    )
    Vacancy.objects.create(
        title='Frontend Developer',
        department=department,
        description='React',
        status=Vacancy.Status.CLOSED,
    )

    response = hr_client.get(reverse('admin-vacancy-export'), data={'status': Vacancy.Status.CLOSED})

    assert response.status_code == 200
    assert response['Content-Type'] == XLSX_CONTENT_TYPE
    assert response['Content-Disposition'] == 'attachment; filename="vacancies.xlsx"'
    sheet_xml = _sheet_xml(response)
    assert 'Frontend Developer' in sheet_xml
    assert 'Backend Developer' not in sheet_xml
