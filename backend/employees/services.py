import logging
import secrets
import string
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils.crypto import get_random_string
from rest_framework.exceptions import ValidationError as DRFValidationError

from employees.models import Employee, EmploymentStatus, Status
from structure.models import Department

logger = logging.getLogger(__name__)

User = get_user_model()


@dataclass
class EmployeeCreate:
    full_name: str
    job_title: str
    email: str
    birthday: date
    department: Department
    user: AbstractBaseUser | None = None
    role_description: list[str] = dataclass_field(default_factory=list)
    phone: str = ''
    interests: str = ''
    personal_email: str | None = None
    personal_phone: str | None = None
    supervisor: Employee | None = None
    city: str | None = None
    employment_status: str = EmploymentStatus.WORKING
    crm_profile: str | None = None
    social_network: str | None = None
    resume_link: str | None = None
    supervisor_role: Department | None = None
    supervisor_photo: Employee | None = None


@dataclass
class EmployeeUpdate:
    full_name: str | None = None
    job_title: str | None = None
    email: str | None = None
    birthday: date | None = None
    department: Department | None = None
    user: AbstractBaseUser | None = None
    role_description: list[str] | None = None
    phone: str | None = None
    personal_email: str | None = None
    personal_phone: str | None = None
    interests: str | None = None
    supervisor: Employee | None = None
    city: str | None = None
    employment_status: str | None = None
    crm_profile: str | None = None
    social_network: str | None = None
    resume_link: str | None = None
    supervisor_role: Department | None = None
    supervisor_photo: Employee | None = None


def _generate_secure_password() -> str:
    """Генерирует безопасный случайный пароль для нового сотрудника."""
    password_length = 12
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()'
    return ''.join(secrets.choice(alphabet) for _ in range(password_length))


def _parse_full_name(full_name: str) -> tuple[str, str]:
    """Разбивает full_name на имя и фамилию."""
    parts = full_name.strip().split(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return full_name, ''


def _send_welcome_email(email: str, password: str, full_name: str) -> bool:
    """Отправляет сотруднику приветственное письмо с учетными данными."""
    subject = 'Добро пожаловать в Книгу Сотрудников!'
    message = (
        f'Здравствуйте, {full_name}!\n\n'
        f'Для вас был создан корпоративный аккаунт.\n'
        f'Используйте следующие данные для входа в систему:\n\n'
        f'Email: {email}\n'
        f'Временный пароль: {password}\n\n'
        f'Пожалуйста, измените пароль после первого входа.'
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error(f'Ошибка отправки приветственного письма на {email}: {str(exc)}')
        return False


def create_employee(data: EmployeeCreate, created_by: AbstractBaseUser | None = None) -> Employee:
    """
    Создаёт сотрудника.

    Если аккаунт пользователя (user) не был передан явно, автоматически
    генерирует для него учетную запись, создает безопасный пароль и отправляет
    уведомление на email через Yandex SMTP.
    """
    if data.user is not None:
        return Employee.objects.create(**data.__dict__, created_by=created_by)

    with transaction.atomic():
        first_name, last_name = _parse_full_name(data.full_name)

        # Генерируем уникальный username (требуется из-за REQUIRED_FIELDS)
        username_salt_length = 5
        username_prefix = data.email.split('@')[0]
        username = f'{username_prefix}_{get_random_string(username_salt_length)}'

        generated_password = _generate_secure_password()

        try:
            user = User.objects.create_user(
                username=username,
                email=data.email,
                password=generated_password,
                first_name=first_name,
                last_name=last_name,
            )
        except Exception as exc:
            logger.error(f'Не удалось создать пользователя для email {data.email}: {str(exc)}')
            raise ValidationError('Пользователь с таким email уже существует в системе.')

        data.user = user
        employee = Employee.objects.create(**data.__dict__, created_by=created_by)

        email_sent = _send_welcome_email(data.email, generated_password, data.full_name)
        if not email_sent:
            raise DRFValidationError(
                {
                    'email': (
                        'Сотрудник не создан: ошибка отправки приветственного письма через SMTP. '
                        'Проверьте конфигурацию почтового сервера.'
                    )
                }
            )

        return employee


def update_employee(employee: Employee, data: EmployeeUpdate, updated_by: AbstractBaseUser | None = None) -> Employee:
    """
    Обновляет данные сотрудника.

    Args:
        employee: Обновляемый сотрудник.
        data: Объект с обновляемыми данными сотрудника.
        updated_by: Пользователь, выполнивший обновление.

    Returns:
        Обновлённый объект сотрудника.
    """
    for field, value in data.__dict__.items():
        if value is not None:
            setattr(employee, field, value)
    if updated_by is not None:
        employee.updated_by = updated_by
    employee.save()
    return employee


def archive_employee(
    employee: Employee,
    updated_by: AbstractBaseUser | None = None,
) -> Employee:
    """
    Архивирует сотрудника через soft delete.

    Args:
        employee: Сотрудник для архивирования.
        updated_by: Пользователь, выполнивший архивирование.

    Returns:
        Архивированный сотрудник.
    """
    employee.status = Status.ARCHIVED
    update_fields = ['status']
    if updated_by is not None:
        employee.updated_by = updated_by
        update_fields.append('updated_by')
    employee.save(update_fields=update_fields)
    return employee
