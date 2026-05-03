# Expedition Service

Django REST API для управління експедиціями з підтримкою WebSocket-сповіщень.

## Стек

Django 4.2, DRF, simplejwt, Django Channels 4 + channels-redis, Daphne, PostgreSQL, Redis, Docker Compose.

## Запуск

```bash
cp .env.example .env
docker compose up -d
pip install -r requirements.txt
python manage.py migrate
```

Для запуску з WebSocket:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Або просто `python manage.py runserver` якщо WebSocket не потрібен.

## Тести

```bash
pip install pytest-mock
pytest
```

## API

### Auth

```
POST /api/auth/register/   - реєстрація (role: chief | member)
POST /api/auth/login/      - отримання токенів
POST /api/auth/refresh/    - оновлення access token
GET  /api/auth/me/         - поточний користувач (потрібен JWT)
```

### Expeditions

```
GET   /api/expeditions/                  - список своїх експедицій
POST  /api/expeditions/                  - створити (тільки chief)
GET   /api/expeditions/{id}/             - деталі
PATCH /api/expeditions/{id}/             - редагувати (тільки chief)

POST  /api/expeditions/{id}/invite/      - запросити учасника (chief)
POST  /api/expeditions/{id}/confirm/     - підтвердити участь (member)

POST  /api/expeditions/{id}/set-ready/    - draft - ready
POST  /api/expeditions/{id}/set-active/   - ready - active
POST  /api/expeditions/{id}/set-finished/ - active - finished
```

### WebSocket

```
ws://localhost:8000/ws/expeditions/{id}/?token=<access_token>
```

Підключитись можуть лише chief та підтверджені члени експедиції. Без токена - код `4001`, якщо немає доступу - `4003`.

Приклади подій:

```
{ "type": "member_invited",    "payload": { "expedition_id": 1, "user_id": 2, "user_name": "User_1" } }
{ "type": "member_confirmed",  "payload": { "expedition_id": 1, "user_id": 2, "user_name": "User_1" } }
{ "type": "expedition_status", "payload": { "expedition_id": 1, "status": "active" } }
```

## Статуси

```
draft - ready - active - finished
```

Перехід в `active` можливий якщо:
- `start_at` вже настав
- щонайменше 2 підтверджених учасники
- їх кількість не перевищує `capacity`
- ніхто з них не бере участі в іншій активній експедиції

Перехід захищений `SELECT FOR UPDATE` від race condition.

## Demo

```bash
python demo/run_demo.py
```

Скрипт реєструє юзерів, створює експедицію, підключає WebSocket-слухачів у фонових потоках і проходить повний lifecycle.
