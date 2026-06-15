import factory
from factory.django import DjangoModelFactory
from faker import Faker

fake = Faker('ru_RU')
Faker.seed(42)


class UserFactory(DjangoModelFactory):
    """Фабрика пользователя (accounts.User).

    Attributes:
        email: Уникальный email, генерируется Faker.
        username: Берётся из локальной части email.
        first_name: Случайное имя на русском.
        last_name: Случайная фамилия на русском.
        role: По умолчанию «employee».
        is_active: Аккаунт активен.
    """

    class Meta:
        model = 'accounts.User'
        django_get_or_create = ('email',)

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    username = factory.LazyAttribute(lambda o: o.email.split('@')[0])
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())

    role = 'employee'
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Устанавливает пароль через set_password.

        Args:
            create: Был ли объект создан в БД.
            extracted: Переданный пароль либо None.
            **kwargs: Дополнительные аргументы FactoryBoy.
        """
        password = extracted or 'demo12345'
        obj.set_password(password)

        if create:
            obj.save(update_fields=['password'])


class HRAdminFactory(UserFactory):
    """Фабрика HR-администратора.

    Наследует UserFactory, переопределяет роль и флаг is_staff.
    """

    role = 'hr_admin'
    is_staff = True


class DirectionFactory(DjangoModelFactory):
    """Фабрика направления верхнего уровня (structure.Department, type='direction').

    Attributes:
        name: Уникальное название компании, генерируется Faker.
        short_name: Первые 10 символов полного названия.
        type: Всегда ``direction``.
        parent: Всегда ``None`` — направление не имеет родителя.
        display_order: Автоинкремент через Sequence.
        is_active: Подразделение активно.
    """

    class Meta:
        model = 'structure.Department'
        django_get_or_create = ('name', 'parent')

    name = factory.LazyAttribute(lambda _: fake.unique.company())
    short_name = factory.LazyAttribute(lambda o: o.name[:10])
    type = 'direction'
    parent = None
    display_order = factory.Sequence(lambda n: n)
    is_active = True


class DepartmentFactory(DjangoModelFactory):
    """Фабрика отдела (structure.Department, type='department').

    Attributes:
        name: Уникальное название компании, генерируется Faker.
        short_name: Первые 10 символов полного названия.
        type: Всегда ``department``.
        parent: Родительское подразделение; по умолчанию ``None``.
        display_order: Автоинкремент через Sequence.
        is_active: Подразделение активно.
    """

    class Meta:
        model = 'structure.Department'
        django_get_or_create = ('name', 'parent')

    name = factory.LazyAttribute(lambda _: fake.unique.company())
    short_name = factory.LazyAttribute(lambda o: o.name[:10])
    type = 'department'
    parent = None
    display_order = factory.Sequence(lambda n: n)
    is_active = True


class TagFactory(DjangoModelFactory):
    """Фабрика тега (tags.Tag).

    Attributes:
        name: Уникальное слово с заглавной буквы, генерируется Faker.
    """

    class Meta:
        model = 'tags.Tag'
        django_get_or_create = ('name',)

    name = factory.LazyAttribute(lambda _: fake.unique.word().capitalize())


class EmployeeFactory(DjangoModelFactory):
    """Фабрика карточки сотрудника (employees.Employee).

    Attributes:
        full_name: ФИО в формате «Фамилия Имя Отчество», генерируется Faker.
        job_title: Должность на русском, генерируется Faker.
        email: Уникальный email, генерируется Faker.
        phone: Номер телефона, генерируется Faker.
        birthday: Дата рождения; возраст от 22 до 60 лет.
        status: По умолчанию ``active``.
        department: Связанный отдел; создаётся через DepartmentFactory.
        user: Связанный пользователь; по умолчанию ``None``.
    """

    class Meta:
        model = 'employees.Employee'
        django_get_or_create = ('email',)

    full_name = factory.LazyAttribute(lambda _: f'{fake.last_name()} {fake.first_name()} {fake.middle_name()}')
    job_title = factory.LazyAttribute(lambda _: fake.job())
    email = factory.LazyAttribute(lambda _: fake.unique.email())
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    birthday = factory.LazyAttribute(lambda _: fake.date_of_birth(minimum_age=22, maximum_age=60))

    status = 'active'
    department = factory.SubFactory(DepartmentFactory)
    user = None
