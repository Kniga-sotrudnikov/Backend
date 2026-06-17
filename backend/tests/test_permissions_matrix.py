import pytest
from django.urls import reverse


# Подготавливаем тестовые данные
@pytest.fixture
def matrix_data(db, department, tag, employee_instance):
    return {
        'dept_id': department.id,
        'tag_id': tag.id,
        'emp_id': employee_instance.id
    }


@pytest.mark.parametrize(
    'url_name, kwargs_factory, method, client_fixture, expected_status',
    [
        # ==========================================
        # ТЕГИ (/api/v1/tags/)
        # ==========================================
        ('tag-list', lambda d: {}, 'get', 'api_client', 401),
        ('tag-list', lambda d: {}, 'get', 'auth_client', 200),
        ('tag-list', lambda d: {}, 'get', 'hr_client', 200),

        ('tag-list', lambda d: {}, 'post', 'auth_client', 403),
        ('tag-list', lambda d: {}, 'post', 'hr_client', 201),

        ('tag-detail', lambda d: {'pk': d['tag_id']}, 'get', 'auth_client', 200),
        ('tag-detail', lambda d: {'pk': d['tag_id']}, 'patch', 'auth_client', 403),
        ('tag-detail', lambda d: {'pk': d['tag_id']}, 'patch', 'hr_client', 200),
        ('tag-detail', lambda d: {'pk': d['tag_id']}, 'delete', 'auth_client', 403),
        ('tag-detail', lambda d: {'pk': d['tag_id']}, 'delete', 'hr_client', 24),  # 204 No Content

        # ==========================================
        # ПОДРАЗДЕЛЕНИЯ (/api/v1/departments/)
        # ==========================================
        ('department-list', lambda d: {}, 'get', 'api_client', 401),
        ('department-list', lambda d: {}, 'get', 'auth_client', 200),
        ('department-list', lambda d: {}, 'post', 'auth_client', 403),
        ('department-list', lambda d: {}, 'post', 'hr_client', 201),

        ('department-detail', lambda d: {'pk': d['dept_id']}, 'get', 'auth_client', 200),
        ('department-detail', lambda d: {'pk': d['dept_id']}, 'patch', 'auth_client', 403),
        ('department-detail', lambda d: {'pk': d['dept_id']}, 'patch', 'hr_client', 200),

        # ==========================================
        # СОТРУДНИКИ И АДМИНКА (/api/v1/admin/employees/)
        # ==========================================
        ('employee-list', lambda d: {}, 'get', 'api_client', 401),
        ('employee-list', lambda d: {}, 'get', 'auth_client', 200),

        # Исправленные имена на 'admin-employee-list'
        ('admin-employee-list', lambda d: {}, 'get', 'auth_client', 403),
        ('admin-employee-list', lambda d: {}, 'get', 'hr_client', 200),
        ('admin-employee-list', lambda d: {}, 'post', 'auth_client', 403),
        ('admin-employee-list', lambda d: {}, 'post', 'hr_client', 201),

        # Исправленные имена на 'admin-employee-detail'
        ('admin-employee-detail', lambda d: {'pk': d['emp_id']}, 'get', 'auth_client', 403),
        ('admin-employee-detail', lambda d: {'pk': d['emp_id']}, 'get', 'hr_client', 200),
        ('admin-employee-detail', lambda d: {'pk': d['emp_id']}, 'patch', 'hr_client', 200),

        # Загрузка фото сотрудника
        ('employee-photo-upload', lambda d: {'id': d['emp_id']}, 'patch', 'auth_client', 403),
        ('employee-photo-upload', lambda d: {'id': d['emp_id']}, 'patch', 'hr_client', 200),
    ]
)
def test_permissions_matrix(request, matrix_data, url_name, kwargs_factory, method, client_fixture, expected_status):
    """Параметризованный тест матрицы прав для различных ролей и методов."""
    client = request.getfixturevalue(client_fixture)
    url = reverse(url_name, kwargs=kwargs_factory(matrix_data))

    payload = {}
    extra_kwargs = {'format': 'json'}

    if url_name == 'tag-list':
        payload = {'name': 'New Matrix Tag'}
    elif url_name == 'department-list':
        payload = {'name': 'New Matrix Dept', 'type': 'department'}
    elif url_name == 'admin-employee-list' and method == 'post':
        payload = {
            'full_name': 'Admin New Employee',
            'job_title': 'QA',
            'email': 'matrix_test@company.com',
            'birthday': '1995-05-05',
            'department': matrix_data['dept_id']
        }
    elif 'patch' in method:
        payload = {'name': 'Updated Name', 'full_name': 'Updated Full Name'}

    # Обработка Multipart для загрузки изображений
    if url_name == 'employee-photo-upload':
        import io
        from PIL import Image

        file_obj = io.BytesIO()
        Image.new('RGB', (10, 10), color='blue').save(file_obj, format='JPEG')
        file_obj.seek(0)
        file_obj.name = 'test.jpg'

        payload = {'photo': file_obj}
        extra_kwargs = {'format': 'multipart'}

    client_method = getattr(client, method)
    response = client_method(url, data=payload, **extra_kwargs)

    if expected_status == 24:
        assert response.status_code == 204
    else:
        assert response.status_code == expected_status
