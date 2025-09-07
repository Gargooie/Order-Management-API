# Order Management API - Тестовое задание Python Developer

REST API для управления заказами с возможностью добавления товаров в заказ

## Запуск проекта

### С Docker 

```bash
# Клонировать репозиторий
git clone <repository-url>
cd order-management-api

# Запустить через Docker Compose
docker-compose up -d

# API будет доступно по адресу http://localhost:8000
```

### Локальный запуск

```bash
# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
export DATABASE_URL="postgresql://user:password@localhost/dbname"

# Запустить сервер
uvicorn order_api:app --reload

# API будет доступно по адресу http://localhost:8000
```

## Тестирование

```bash
# Запуск тестов
pytest tests.py -v
```