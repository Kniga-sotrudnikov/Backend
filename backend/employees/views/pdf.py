from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from employees.models import Employee
from employees.serializers.employee import EmployeeDetailSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from weasyprint import HTML


class EmployeePDFExportView(APIView):
    """
    Эндпоинт для экспорта карточки сотрудника в формате PDF.

    GET /api/v1/employees/{id}/export/pdf/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        employee = get_object_or_404(Employee, id=id, is_deleted=False)
        serializer = EmployeeDetailSerializer(employee, context={'request': request})
        employee_data = serializer.data

        html_content = render_to_string(
            'employees/pdf/card.html',
            {
                'employee': employee_data,
                'request': request,
            },
        )

        try:
            base_url = f'file://{settings.BASE_DIR}/static/'
            pdf_file = HTML(string=html_content, base_url=base_url).write_pdf()
        except Exception:
            raise

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="employee_{id}.pdf"'
        return response
