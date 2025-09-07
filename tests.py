
# -*- coding: utf-8 -*-
"""
Тесты для Order Management API
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from order_api import app, get_db, Base
import json

# Тестовая база данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Переопределяем dependency для тестов
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Создаем тестовые таблицы
Base.metadata.create_all(bind=engine)

client = TestClient(app)

@pytest.fixture
def setup_test_data():
    """Создает тестовые данные для каждого теста"""
    db = TestingSessionLocal()
    
    # Очищаем таблицы
    db.execute("DELETE FROM order_items")
    db.execute("DELETE FROM orders") 
    db.execute("DELETE FROM products")
    db.execute("DELETE FROM categories")
    db.execute("DELETE FROM clients")
    
    # Создаем тестовые данные
    from order_api import Category, Product, Client, Order
    
    # Категории
    category = Category(id=1, name="Электроника", parent_id=None, level=0, path="1")
    db.add(category)
    
    # Товары
    product1 = Product(id=1, name="Смартфон", quantity=10, price=50000.00, category_id=1)
    product2 = Product(id=2, name="Ноутбук", quantity=5, price=80000.00, category_id=1)
    db.add_all([product1, product2])
    
    # Клиенты
    client_data = Client(id=1, name="Тестовый клиент", address="Тестовый адрес")
    db.add(client_data)
    
    # Заказы
    order = Order(id=1, client_id=1, status="pending")
    db.add(order)
    
    db.commit()
    db.close()

def test_root_endpoint():
    """Тест корневого эндпоинта"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Order Management API" in data["message"]

def test_add_item_to_order_new_item(setup_test_data):
    """Тест добавления нового товара в заказ"""
    request_data = {
        "order_id": 1,
        "product_id": 1,
        "quantity": 2
    }
    
    response = client.post("/orders/add-item", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["total_quantity"] == 2
    assert data["order_item_id"] is not None
    assert "добавлен в заказ" in data["message"]

def test_add_item_to_order_existing_item(setup_test_data):
    """Тест увеличения количества существующего товара в заказе"""
    # Сначала добавляем товар
    request_data = {
        "order_id": 1,
        "product_id": 1,
        "quantity": 2
    }
    client.post("/orders/add-item", json=request_data)
    
    # Затем добавляем тот же товар еще раз
    request_data["quantity"] = 3
    response = client.post("/orders/add-item", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["total_quantity"] == 5  # 2 + 3
    assert "увеличено" in data["message"]

def test_add_item_insufficient_stock(setup_test_data):
    """Тест ошибки при недостатке товара на складе"""
    request_data = {
        "order_id": 1,
        "product_id": 1,
        "quantity": 15  # Больше чем есть на складе (10)
    }
    
    response = client.post("/orders/add-item", json=request_data)
    assert response.status_code == 409
    
    data = response.json()
    assert "Недостаточно товара на складе" in data["detail"]["error"]

def test_add_item_order_not_found(setup_test_data):
    """Тест ошибки при несуществующем заказе"""
    request_data = {
        "order_id": 999,  # Несуществующий заказ
        "product_id": 1,
        "quantity": 1
    }
    
    response = client.post("/orders/add-item", json=request_data)
    assert response.status_code == 404
    
    data = response.json()
    assert "Заказ не найден" in data["detail"]["error"]

def test_add_item_product_not_found(setup_test_data):
    """Тест ошибки при несуществующем товаре"""
    request_data = {
        "order_id": 1,
        "product_id": 999,  # Несуществующий товар
        "quantity": 1
    }
    
    response = client.post("/orders/add-item", json=request_data)
    assert response.status_code == 404
    
    data = response.json()
    assert "Товар не найден" in data["detail"]["error"]

def test_add_item_invalid_data():
    """Тест валидации входных данных"""
    # Отрицательное количество
    request_data = {
        "order_id": 1,
        "product_id": 1,
        "quantity": -1
    }
    
    response = client.post("/orders/add-item", json=request_data)
    assert response.status_code == 422  # Validation error

def test_get_order(setup_test_data):
    """Тест получения информации о заказе"""
    # Сначала добавляем товар в заказ
    request_data = {
        "order_id": 1,
        "product_id": 1,
        "quantity": 2
    }
    client.post("/orders/add-item", json=request_data)
    
    # Получаем информацию о заказе
    response = client.get("/orders/1")
    assert response.status_code == 200
    
    data = response.json()
    assert "order" in data
    assert "items" in data
    assert data["order"]["id"] == 1
    assert len(data["items"]) == 1

def test_get_order_not_found(setup_test_data):
    """Тест получения несуществующего заказа"""
    response = client.get("/orders/999")
    assert response.status_code == 404

def test_get_product(setup_test_data):
    """Тест получения информации о товаре"""
    response = client.get("/products/1")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Смартфон"
    assert data["price"] == 50000.0
    assert data["quantity"] == 10

def test_get_product_not_found(setup_test_data):
    """Тест получения несуществующего товара"""
    response = client.get("/products/999")
    assert response.status_code == 404

def test_order_total_calculation(setup_test_data):
    """Тест автоматического пересчета суммы заказа"""
    # Добавляем первый товар
    request_data1 = {
        "order_id": 1,
        "product_id": 1,
        "quantity": 2  # 2 * 50000 = 100000
    }
    response1 = client.post("/orders/add-item", json=request_data1)
    assert response1.json()["order_total"] == 100000.0
    
    # Добавляем второй товар
    request_data2 = {
        "order_id": 1,
        "product_id": 2,
        "quantity": 1  # 1 * 80000 = 80000
    }
    response2 = client.post("/orders/add-item", json=request_data2)
    # Общая сумма: 100000 + 80000 = 180000
    assert response2.json()["order_total"] == 180000.0

def test_stock_deduction(setup_test_data):
    """Тест уменьшения остатков товара на складе"""
    # Проверяем начальное количество
    response = client.get("/products/1")
    initial_quantity = response.json()["quantity"]
    assert initial_quantity == 10
    
    # Добавляем товар в заказ
    request_data = {
        "order_id": 1,
        "product_id": 1,
        "quantity": 3
    }
    client.post("/orders/add-item", json=request_data)
    
    # Проверяем, что количество уменьшилось
    response = client.get("/products/1")
    new_quantity = response.json()["quantity"]
    assert new_quantity == initial_quantity - 3

def test_api_documentation():
    """Тест доступности документации API"""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/redoc")  
    assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
