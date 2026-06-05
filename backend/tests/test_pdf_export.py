import pytest
from datetime import date
from django.urls import reverse

from structure.models import Department
from employees.models import Employee


@pytest.fixture
def department(db):
    """Тестовый департамент."""

    return Department.objects.create(
        name="IT",
        type="department",
    )


@pytest.fixture
def employee_factory(db, department):
    """
    Factory для создания Employee в тестах.
    """

    def create_employee(
        full_name='Иван Иванов',
        job_title='Разработчик',
        email='ivanov@example.com',
        phone='+70000000000',
        birthday=date(1995, 1, 1),
        department=department,
        **extra_fields,
    ):
        return Employee.objects.create(
            full_name=full_name,
            job_title=job_title,
            email=email,
            phone=phone,
            birthday=birthday,
            department=department,
            **extra_fields,
        )

    return create_employee


@pytest.mark.django_db
class TestEmployeePDFExport:

    def test_pdf_export_requires_authentication(self, api_client, employee_factory):
        """
        Проверка, что аутентифицированный пользователь
        может скачать pdf карточку сотрудника.
        """
        employee = employee_factory()

        url = reverse('employee-pdf-export', kwargs={'id': employee.id})
        response = api_client.get(url)

        assert response.status_code == 401

    def test_pdf_export_returns_404_for_nonexistent_id(self, auth_client):
        """Проверка работы фильтрации несуществующих id."""
        fake_id = 222

        url = reverse('employee-pdf-export', kwargs={'id': fake_id})
        response = auth_client.get(url)

        assert response.status_code == 404

    def test_pdf_export_returns_pdf_content_type(self, auth_client, employee_factory):
        """Проверка типа возвращаемых данных."""
        employee = employee_factory()

        url = reverse('employee-pdf-export', kwargs={'id': employee.id})
        response = auth_client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'

    def test_pdf_export_has_content_disposition(self, auth_client, employee_factory):
        """Проверка content disposition."""
        employee = employee_factory()

        url = reverse('employee-pdf-export', kwargs={'id': employee.id})
        response = auth_client.get(url)

        assert response.status_code == 200
        assert 'attachment' in response['Content-Disposition']
        assert f'employee_{employee.id}.pdf' in response['Content-Disposition']

    def test_pdf_export_with_all_fields(self, auth_client, employee_factory):
        """Проверка экспорта карточки сотрудника со всеми полями."""
        employee = employee_factory(
            full_name='Александр Алексеев',
            job_title='Старший разработчик',
            email='alexeyev@example.com',
            phone='+7 999 123-45-67',
            birthday=date(1990, 5, 15),
        )

        url = reverse('employee-pdf-export', kwargs={'id': employee.id})
        response = auth_client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
