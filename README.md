# Python Diploma Project

Django REST API для сервиса закупок: пользователи регистрируются, подтверждают email, просматривают товары поставщиков, управляют корзиной, оформляют заказы, а поставщики обновляют прайс-листы и управляют приемом заказов.

## Стек

- Python 3.13
- Django
- Django REST Framework
- Celery
- Redis
- SQLite
- PyYAML
- pytest
- Docker Compose

## Быстрый запуск через Docker

Создайте `.env` в корне проекта по примеру `.env.example`:

```env
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

DJANGO_SETTINGS_MODULE=config.settings

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

EMAIL_BACKEND=orders.email_backends.ReadableConsoleEmailBackend
DEFAULT_FROM_EMAIL=noreply@example.com
ADMIN_EMAIL=admin@example.com
```

Соберите и запустите контейнеры:

```powershell
docker compose build
docker compose up
```

При старте `web` контейнер применяет миграции и запускает сервер:

```text
http://localhost:8000
```

## Локальный запуск без Docker

Создайте и активируйте виртуальное окружение, затем установите зависимости:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Примените миграции и запустите сервер:

```powershell
python manage.py migrate
python manage.py runserver
```

Для Celery локально должен быть доступен Redis:

```powershell
celery -A config worker -l info
```

## API

Базовый URL:

```text
http://localhost:8000/api/v1
```

Основные endpoint:

```text
POST   /user/register
POST   /user/register/confirm
POST   /user/login
GET    /user/details
POST   /user/details
POST   /user/password_reset
POST   /user/password_reset/confirm

GET    /user/contact
POST   /user/contact
PUT    /user/contact
DELETE /user/contact

GET    /shops
GET    /categories
GET    /products

GET    /basket
POST   /basket
PUT    /basket
DELETE /basket

GET    /order
POST   /order

POST   /partner/update
GET    /partner/state
POST   /partner/state
GET    /partner/orders
```

Защищенные endpoint используют DRF token auth:

```http
Authorization: Token <token>
```

Токен возвращается после успешного входа:

```text
POST /api/v1/user/login
```

## Email

По умолчанию для локальной разработки используется читаемый консольный backend:

```env
EMAIL_BACKEND=orders.email_backends.ReadableConsoleEmailBackend
```

Письма подтверждения регистрации и сброса пароля выводятся в логах контейнера `celery`:

```powershell
docker compose logs -f celery
```

## Импорт прайса поставщика

Поставщик отправляет ссылку на YAML-файл:

```text
POST /api/v1/partner/update
```

Пример form-data:

```text
url=https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml
```

Импорт запускается через Celery. Статус выполнения смотрите в логах `celery`.

Также импорт YAML доступен через Django Admin на странице товарных позиций. Для этого используются кастомные admin-шаблоны: `orders/templates/admin/orders/productinfo/change_list.html` и `orders/templates/admin/orders/productinfo/import_yaml.html`.

## Тесты

Запуск тестов:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Если нужно отключить pytest cache:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

### Что проверяют тесты

Тесты находятся в каталоге `orders/tests/` и покрывают основные сценарии API и бизнес-логики:

- `test_api_auth.py` проверяет регистрацию, подтверждение email, вход, просмотр и обновление профиля, сброс пароля.
- `test_api_contacts.py` проверяет создание, получение, обновление и удаление контактов пользователя.
- `test_api_products.py` проверяет публичные endpoint для списка товаров, магазинов и категорий.
- `test_api_basket.py` проверяет полный цикл работы с корзиной: добавление, просмотр, изменение количества и удаление товаров.
- `test_api_orders.py` проверяет оформление корзины в заказ и получение списка заказов пользователя.
- `test_api_partner.py` проверяет endpoint поставщика: обновление прайса, изменение статуса приема заказов и просмотр заказов магазина.
- `test_import.py` проверяет импорт товаров из YAML-файла на уровне сервисного слоя.
- `test_tasks.py` проверяет Celery-задачи отправки email и импорта товаров.
- `test_models.py` проверяет строковые представления основных моделей.

Во время тестов Celery работает в eager-режиме, а письма сохраняются в памяти через Django `locmem` email backend. Это позволяет проверять фоновые задачи и email-сценарии без Redis и реальной почты.

## Структура проекта

```text
config/              настройки Django, URL проекта, Celery
orders/              основное приложение
orders/models.py     модели пользователей, магазинов, товаров и заказов
orders/serializers.py serializers для API
orders/views.py      API views
orders/services.py   импорт товаров из YAML
orders/tasks.py      Celery-задачи
orders/templates/    кастомные шаблоны Django Admin для импорта YAML
orders/tests/        тесты
import_data/         пример YAML-файла
```

## Важные замечания

- Redis внутри Docker доступен сервисам по адресу `redis:6379`.
