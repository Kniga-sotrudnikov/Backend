"""Management-команда для наполнения БД демо-данными.

Запуск::

    python backend/manage.py seed_demo
    python backend/manage.py seed_demo --flush

Учётные записи после выполнения::

    hr1 @ demo.local / demo12345(HR - admin)
    hr2 @ demo.local / demo12345(HR - admin)
    emp1 @ demo.local / demo12345(employee)
    emp2 @ demo.local / demo12345(employee)
    emp3 @ demo.local / demo12345(employee)
    emp4 @ demo.local / demo12345(employee)
    emp5 @ demo.local / demo12345(employee)
"""

import random

from django.core.management.base import BaseCommand
from tests.factories.factories import (
    DepartmentFactory,
    DirectionFactory,
    EmployeeFactory,
    HRAdminFactory,
    TagFactory,
    UserFactory,
    fake,
)

random.seed(42)

DEMO_PASSWORD = 'demo12345'

DIRECTION_NAMES = [
    'Технологии и разработка',
    'Маркетинг и продажи',
    'Операционная деятельность',
]

DEPARTMENT_TREE = {
    'Технологии и разработка': ['Разработка ПО', 'DevOps и инфраструктура', 'QA и тестирование'],
    'Маркетинг и продажи': ['Цифровой маркетинг', 'Отдел продаж', 'Аналитика'],
    'Операционная деятельность': ['HR и кадры', 'Финансы', 'Административный отдел'],
}

TAG_DATA = [
    ('Python', '#3572A5'),
    ('Django', '#092E20'),
    ('Менторство', '#FF8C00'),
    ('Удалённая работа', '#6A5ACD'),
    ('Командная игра', '#20B2AA'),
    ('Аналитика', '#DC143C'),
    ('Лидерство', '#DAA520'),
    ('Дизайн', '#FF69B4'),
    ('DevOps', '#2E8B57'),
    ('Agile', '#4169E1'),
]

JOB_TITLES = [
    'Backend-разработчик',
    'Frontend-разработчик',
    'DevOps-инженер',
    'QA-инженер',
    'Продакт-менеджер',
    'Аналитик данных',
    'HR-специалист',
    'Руководитель проекта',
    'Системный архитектор',
    'Маркетолог',
    'Финансовый аналитик',
    'Технический писатель',
]


class Command(BaseCommand):
    """Заполняет БД воспроизводимыми демо-данными на русском языке.

    Идемпотентна: повторный запуск не создаёт дублей благодаря
    ``get_or_create`` внутри фабрик. Флаг ``--flush`` предварительно
    удаляет все объекты с доменом ``@demo.local``.
    """

    help = 'Заполнить БД демо-данными (идемпотентно).'

    def add_arguments(self, parser):
        """Регистрирует аргументы командной строки.

        Args:
            parser: Экземпляр ArgumentParser Django.
        """
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Удалить существующие демо-данные перед созданием.',
        )

    def handle(self, *args, **options):
        """Точка входа команды.

        Args:
            *args: Позиционные аргументы Django.
            **options: Именованные аргументы; обрабатывает ключ ``flush``.
        """
        if options['flush']:
            self._flush()

        emp_users = self._seed_users()
        departments = self._seed_structure()
        tags = self._seed_tags()
        self._seed_employees(departments, tags, emp_users)
        self._print_summary()

    def _flush(self):
        """Удаляет все демо-объекты с доменом ``@demo.local``.

        Порядок удаления соблюдает ограничения PROTECT:
        сначала дочерние отделы, затем направления.
        """
        from django.contrib.auth import get_user_model
        from employees.models import Employee

        from structure.models import Department
        from tags.models import EmployeeTag, Tag

        User = get_user_model()
        self.stdout.write(self.style.WARNING('Удаляем демо-данные...'))

        EmployeeTag.objects.filter(employee__email__contains='@demo.local').delete()
        Employee.objects.filter(email__contains='@demo.local').delete()
        Tag.objects.filter(name__in=[name for name, _ in TAG_DATA]).delete()
        Department.objects.filter(
            type=Department.Type.DEPARTMENT,
            name__in=[d for deps in DEPARTMENT_TREE.values() for d in deps],
        ).delete()
        Department.objects.filter(
            type=Department.Type.DIRECTION,
            name__in=DIRECTION_NAMES,
        ).delete()
        User.objects.filter(email__contains='@demo.local').delete()
        self.stdout.write(self.style.WARNING('Готово.\n'))

    def _seed_users(self):
        """Создаёт 2 HR-администраторов и 5 пользователей-сотрудников.

        Returns:
            Список из 5 объектов User с ролью ``employee``.
        """
        HRAdminFactory(
            email='hr1@demo.local',
            username='hr1',
            first_name='Анна',
            last_name='Иванова',
            password=DEMO_PASSWORD,
        )
        HRAdminFactory(
            email='hr2@demo.local',
            username='hr2',
            first_name='Дмитрий',
            last_name='Петров',
            password=DEMO_PASSWORD,
        )

        emp_users = []
        for i in range(1, 6):
            user = UserFactory(
                email=f'emp{i}@demo.local',
                username=f'emp{i}',
                password=DEMO_PASSWORD,
            )
            emp_users.append(user)
        return emp_users

    def _seed_structure(self):
        """Создаёт 3 направления и по 3 отдела под каждым.

        Returns:
            Список из 9 объектов Department с типом ``department``.
        """
        departments = []
        for i, dir_name in enumerate(DIRECTION_NAMES):
            direction = DirectionFactory(name=dir_name, parent=None, display_order=i)
            for j, dep_name in enumerate(DEPARTMENT_TREE[dir_name]):
                dept = DepartmentFactory(name=dep_name, parent=direction, display_order=j)
                departments.append(dept)
        return departments

    def _seed_tags(self):
        """Создаёт 10 тегов с фиксированными названиями и цветами.

        Returns:
            Список из 10 объектов Tag.
        """
        return [TagFactory(name=name, color_or_icon=color) for name, color in TAG_DATA]

    def _seed_employees(self, departments, tags, emp_users):
        """Создаёт 18 карточек сотрудников и назначает им случайные теги.

        Первые 5 карточек привязываются к известным пользователям из
        ``emp_users``; остальные 13 создаются без привязки к User.
        Каждому сотруднику назначается от 1 до 3 тегов через EmployeeTag.

        Args:
            departments: Список доступных отделов для случайного выбора.
            tags: Список доступных тегов для случайного выбора.
            emp_users: Список пользователей для привязки к первым карточкам.
        """
        from tags.models import EmployeeTag

        for i in range(18):
            linked_user = emp_users[i] if i < len(emp_users) else None

            employee = EmployeeFactory(
                email=f'demo_emp_{i + 1}@demo.local',
                full_name=f'{fake.last_name()} {fake.first_name()} {fake.middle_name()}',
                job_title=random.choice(JOB_TITLES),
                birthday=fake.date_of_birth(minimum_age=22, maximum_age=60),
                department=random.choice(departments),
                user=linked_user,
            )

            for tag in random.sample(tags, k=random.randint(1, 3)):
                EmployeeTag.objects.get_or_create(employee=employee, tag=tag)

    def _print_summary(self):
        """Выводит в stdout итоговую таблицу созданных учётных записей и структуры."""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Демо-данные успешно созданы!'))
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('HR-администраторы:'))
        self.stdout.write(f'  hr1@demo.local  /  {DEMO_PASSWORD}')
        self.stdout.write(f'  hr2@demo.local  /  {DEMO_PASSWORD}')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Сотрудники (с логином):'))
        for i in range(1, 6):
            self.stdout.write(f'  emp{i}@demo.local  /  {DEMO_PASSWORD}')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Оргструктура:'))
        for dir_name, deps in DEPARTMENT_TREE.items():
            self.stdout.write(f'  {dir_name}')
            for dep in deps:
                self.stdout.write(f'    - {dep}')
        self.stdout.write('')
