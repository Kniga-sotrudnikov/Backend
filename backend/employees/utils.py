from datetime import date, timedelta

from django.utils import timezone


def get_birthday_days_condition(days_ahead: int) -> list[tuple[int, int]]:
    """Возвращает список пар (месяц, день) на N дней вперед."""
    today = timezone.now().date()
    target_pairs = []

    for i in range(days_ahead + 1):
        future_date = today + timedelta(days=i)
        month = future_date.month
        day = future_date.day
        target_pairs.append((month, day))

        # Если текущий год невисокосный и мы обрабатываем 28 февраля,
        # добавляем людей, родившихся 29 февраля
        is_leap = future_date.year % 4 == 0 and (future_date.year % 100 != 0 or future_date.year % 400 == 0)
        if month == 2 and day == 28 and not is_leap:
            target_pairs.append((2, 29))

    return target_pairs


def calculate_days_until_birthday(birthday: date) -> int:
    """Вычисляет сколько дней осталось до ДР."""
    if not birthday:
        return 999
    today = timezone.now().date()

    # Пробуем текущий год. Для родившихся 29 февраля в невисокосный год — сдвигаем на 28 февраля
    try:
        b_this_year = birthday.replace(year=today.year)
    except ValueError:
        b_this_year = birthday.replace(year=today.year, month=2, day=28)

    if b_this_year < today:
        # Если ДР уже прошел в этом году, смотрим на следующий год
        try:
            b_this_year = birthday.replace(year=today.year + 1)
        except ValueError:
            b_this_year = birthday.replace(year=today.year + 1, month=2, day=28)

    return (b_this_year - today).days
