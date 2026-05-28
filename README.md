
# Проект "Книга сотрудников"
Backend на Django DRF для веб-сайта.

## 🛠️ Старт локальной разработки в Docker

### Создаем файл с переменными окружения:
```bash
cp  .env.example  .env
```

### Запуск сервисов:
*Если локальных `docker images` нет — они будут загружены из DockerHub или собраны автоматически.*
```bash
docker  compose  up  -d
```
Поднимает все сервисы: web, postgres, redis, celery_worker, celery_beat.

### Применяем миграции и создаем суперпользователя:
```bash
docker  compose  exec  -it  web  python  backend/manage.py  migrate
docker  compose  exec  -it  web  python  backend/manage.py  createsuperuser
```
> Примечание: команда migrate применяет в том числе миграции django_celery_beat (таблицы для периодических задач Celery).

### Доступ к приложению
* Откройте http://localhost:8000/ в браузере

## Установка новых зависимостей
###  Устанавливаем
```bash
docker  compose  exec  -it  web  pip install <new_lib_name>
```
###  Фиксируем новое окружение в файле для pip 
```bash
docker  compose  exec  -it  web pip freeze > ./requirements.txt
```
###  Пересобираем образ приложения с новым окружением и перестартуем проект  
```bash
docker compose build web
docker compose up -d
```

## ✅ Проверка кода перед PullRequest

Форматируем:
```bash
docker  compose  run  --rm  -it  web  ruff  format
```

Исправляем более существенные проблемы (неиспользуемые импорты и т.п.):
```bash
docker compose exec web ruff check . --fix
```

Запуск всех проверок и тестов так же, как при production-деплое.
Должен завершится `[ci finished]`:

```bash
docker  compose  run  --rm  -it  web  bash  ./docker/django/ci.sh
```


## 🔄 Команды обслуживания и решение проблем

Очистка проекта (удаляет volumes, включая базу данных):
```bash
docker  compose  down  -v
```

Пересборка контейнера (если изменились зависимости или возникли проблемы):
```bash
docker  compose  build  web
docker  compose  up  -d
```
