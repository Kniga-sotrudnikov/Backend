"""Проверки конфигурации логирования (settings.LOGGING)."""

import importlib.util
import logging
import logging.config
import sys
from pathlib import Path

import pytest
from django.conf import settings


SETTINGS_PATH = Path(__file__).resolve().parents[1] / 'employeebook' / 'settings.py'
ENV_PATH = SETTINGS_PATH.parents[2] / '.env'


def load_settings(monkeypatch, **env):
    """Загружает settings.py изолированно с подменёнными переменными окружения.

    Тест не должен зависеть от содержимого локального .env, поэтому репозиторий
    decouple подменяется копией без ключей, которыми управляет сам тест.
    Значение None означает «переменная не задана нигде».
    """
    from decouple import RepositoryEnv

    repository = dict(RepositoryEnv(ENV_PATH).data)
    for key, value in env.items():
        repository.pop(key, None)
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    monkeypatch.setattr('decouple.RepositoryEnv', lambda source: repository)

    spec = importlib.util.spec_from_file_location('_settings_probe', SETTINGS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def apply_logging():
    """Применяет переданный LOGGING и восстанавливает боевой конфиг после теста."""
    yield logging.config.dictConfig
    logging.config.dictConfig(settings.LOGGING)


# --- Матрица: уровень корневого логгера ---


def test_dev_defaults_to_debug(monkeypatch):
    """DEBUG=True без LOG_LEVEL -> корневой логгер на DEBUG."""
    probe = load_settings(monkeypatch, DEBUG='True', LOG_LEVEL=None)
    assert probe.LOGGING['root']['level'] == 'DEBUG'
    assert probe.LOGGING['root']['handlers'] == ['console']


def test_prod_defaults_to_info(monkeypatch):
    """DEBUG=False без LOG_LEVEL -> корневой логгер на INFO."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL=None)
    assert probe.LOGGING['root']['level'] == 'INFO'


def test_log_level_overrides_debug_default(monkeypatch):
    """LOG_LEVEL из окружения побеждает значение по умолчанию."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL='DEBUG')
    assert probe.LOGGING['root']['level'] == 'DEBUG'


def test_file_handler_is_gone(monkeypatch):
    """Файловый хендлер и его фильтр удалены — логи только в stdout."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL=None)
    assert set(probe.LOGGING['handlers']) == {'console'}
    assert 'filters' not in probe.LOGGING
    for handler in probe.LOGGING['handlers'].values():
        assert handler['class'] == 'logging.StreamHandler'


# --- Матрица: фактический вывод ---


def test_app_info_reaches_stdout_in_dev(monkeypatch, capsys, apply_logging):
    """DEBUG=True: logger.info() из приложения попадает в консоль с меткой и именем."""
    probe = load_settings(monkeypatch, DEBUG='True', LOG_LEVEL=None)
    apply_logging(probe.LOGGING)
    logging.getLogger('employees.services').info('LOGCHECK-DEV')

    captured = capsys.readouterr().err
    assert 'LOGCHECK-DEV' in captured
    assert 'INFO' in captured
    assert 'employees.services' in captured


def test_app_info_reaches_stdout_in_prod(monkeypatch, capsys, apply_logging):
    """DEBUG=False: logger.info() из приложения по-прежнему виден."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL=None)
    apply_logging(probe.LOGGING)
    logging.getLogger('notifications.tasks').info('LOGCHECK-PROD')

    assert 'LOGCHECK-PROD' in capsys.readouterr().err


def test_app_debug_suppressed_in_prod(monkeypatch, capsys, apply_logging):
    """DEBUG=False без LOG_LEVEL: logger.debug() не выводится."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL=None)
    apply_logging(probe.LOGGING)
    logging.getLogger('employees.views.employee').debug('LOGCHECK-QUIET')

    assert 'LOGCHECK-QUIET' not in capsys.readouterr().err


def test_app_debug_enabled_by_log_level(monkeypatch, capsys, apply_logging):
    """LOG_LEVEL=DEBUG: logger.debug() доходит до консоли."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL='DEBUG')
    apply_logging(probe.LOGGING)
    logging.getLogger('employees.services').debug('LOGCHECK-VERBOSE')

    assert 'LOGCHECK-VERBOSE' in capsys.readouterr().err


def test_sql_not_flooded_at_debug(monkeypatch, capsys, apply_logging, db):
    """LOG_LEVEL=DEBUG не открывает поток SQL-запросов."""
    from django.contrib.contenttypes.models import ContentType

    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL='DEBUG')
    apply_logging(probe.LOGGING)
    logging.getLogger('django.db.backends').debug('SELECT "sentinel"')
    list(ContentType.objects.all()[:1])

    assert 'SELECT' not in capsys.readouterr().err


def test_request_line_logged_once(monkeypatch, capsys, apply_logging):
    """Строка запроса Django печатается ровно один раз, без дубля через root."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL='DEBUG')
    apply_logging(probe.LOGGING)
    logging.getLogger('django.server').info('"GET /api/v1/employees/ HTTP/1.1" 200 42')

    assert capsys.readouterr().err.count('GET /api/v1/employees/') == 1


def test_request_exception_logged_once(monkeypatch, capsys, apply_logging):
    """Трейсбек django.request печатается один раз и содержит исключение."""
    probe = load_settings(monkeypatch, DEBUG='False', LOG_LEVEL=None)
    apply_logging(probe.LOGGING)
    try:
        raise ValueError('LOGCHECK-BOOM')
    except ValueError:
        logging.getLogger('django.request').exception('Internal Server Error: /api/v1/employees/')

    captured = capsys.readouterr().err
    assert captured.count('Internal Server Error: /api/v1/employees/') == 1
    assert 'LOGCHECK-BOOM' in captured
    assert 'Traceback' in captured


def test_probe_module_is_not_registered():
    """Изолированная загрузка settings не подменяет боевой модуль."""
    assert '_settings_probe' not in sys.modules
