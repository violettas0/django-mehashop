# django-mehashop
# Django Mehashop

Django Mehashop - это платформа для электронной коммерции, построенная на Django, Django Rest Framework и различных сторонних пакетах для обеспечения комплексного решения для интернет-магазина.

## Возможности

- Аутентификация и авторизация пользователей
- Каталог продуктов с категориями
- Корзина покупок и обработка заказов
- Интеграция платежей с YooKassa
- Социальная аутентификация через VK и Yandex
- API для взаимодействия с фронтендом

## Установка

### Предварительные требования

- Python 3.8 или выше
- Docker (опционально, для контейнеризации)
- PostgreSQL (или любая другая поддерживаемая база данных)
- Redis (для Celery)

### Клонирование репозитория

```bash
git clone https://github.com/violettas0/django-mehashop.git
cd django-mehashop
```

### Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # На Windows используйте `venv\Scripts\activate`
```

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка переменных окружения

Создайте файл `.env` в корне проекта и добавьте следующие переменные окружения:

```plaintext
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_NAME=your_database_name
DATABASE_USER=your_database_user
DATABASE_PASSWORD=your_database_password
DATABASE_HOST=your_database_host
DATABASE_PORT=your_database_port
SOCIAL_AUTH_VK_OAUTH2_KEY=your_vk_oauth2_key
SOCIAL_AUTH_VK_OAUTH2_SECRET=your_vk_oauth2_secret
SOCIAL_AUTH_YANDEX_OAUTH2_KEY=your_yandex_oauth2_key
SOCIAL_AUTH_YANDEX_OAUTH2_SECRET=your_yandex_oauth2_secret
YOOKASSA_LOGIN=your_yookassa_login
YOOKASSA_SECRET_KEY=your_yookassa_secret_key
```

### Применение миграций

```bash
python manage.py migrate
```

### Создание суперпользователя

```bash
python manage.py createsuperuser
```

### Загрузка тестовых данных (опционально)

```bash
python manage.py loaddata test_data.json
```

### Запуск сервера разработки

```bash
python manage.py runserver
```

## Запуск с Docker

### Сборка и запуск контейнеров

```bash
docker-compose up --build
```

### Применение миграций в Docker

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Запуск тестов

Для запуска тестов используйте следующую команду:

```bash
python manage.py test
```

## API Эндпоинты

- `/api/products/` - Список и создание продуктов
- `/api/products/<id>/` - Получение, обновление или удаление продукта
- `/api/categories/` - Список категорий
- `/api/cart/` - Получение корзины текущего пользователя
- `/api/orders/` - Создание заказа


## Лицензия

Этот проект лицензирован под MIT License.
