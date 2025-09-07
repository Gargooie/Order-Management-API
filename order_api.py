# -*- coding: utf-8 -*-
"""
REST API сервис для добавления товара в заказ
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import os

# SQLAlchemy 2.x стиль подключения с psycopg3

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://your_postgres_username:your_password@localhost/testdb")

engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)
Base = declarative_base()

# Модели SQLAlchemy
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    level = Column(Integer, nullable=False, default=0)
    path = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='check_quantity_positive'),
        CheckConstraint('price >= 0', name='check_price_positive'),
    )

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    orders = relationship("Order", back_populates="client")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")
    total_amount = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    client = relationship("Client", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    __table_args__ = (
        UniqueConstraint('order_id', 'product_id', name='unique_order_product'),
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('price >= 0', name='check_price_positive'),
    )

# Pydantic модели для API
class AddItemRequest(BaseModel):
    order_id: int = Field(..., gt=0, description="ID заказа")
    product_id: int = Field(..., gt=0, description="ID товара")
    quantity: int = Field(..., gt=0, description="Количество товара")
    class Config:
        schema_extra = {
            "example": {
                "order_id": 1,
                "product_id": 5,
                "quantity": 2
            }
        }

class AddItemResponse(BaseModel):
    success: bool
    message: str
    order_item_id: Optional[int] = None
    total_quantity: int
    order_total: Optional[float] = None
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Товар успешно добавлен в заказ",
                "order_item_id": 15,
                "total_quantity": 3,
                "order_total": 1500.00
            }
        }

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None

# Создание таблиц
Base.metadata.create_all(bind=engine)

# FastAPI приложение
app = FastAPI(
    title="Order Management API",
    description="REST API для управления заказами - Тестовое задание Python Developer",
    version="1.0.0"
)

# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_order_total(db: Session, order_id: int):
    """Обновляет общую сумму заказа"""
    total = db.query(func.sum(OrderItem.quantity * OrderItem.price)).filter(OrderItem.order_id == order_id).scalar() or 0
    db.query(Order).filter(Order.id == order_id).update({"total_amount": total, "updated_at": datetime.utcnow()})
    db.commit()

@app.post("/orders/add-item", response_model=AddItemResponse, responses={
        400: {"model": ErrorResponse, "description": "Неверные данные запроса"},
        404: {"model": ErrorResponse, "description": "Заказ или товар не найден"},
        409: {"model": ErrorResponse, "description": "Недостаточно товара на складе"}
    }, summary="Добавление товара в заказ")
def add_item_to_order(request: AddItemRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == request.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Заказ не найден", "details": f"Заказ с ID {request.order_id} не существует"})
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Товар не найден", "details": f"Товар с ID {request.product_id} не существует"})
    if product.quantity < request.quantity:
        raise HTTPException(status_code=409, detail={"success": False, "error": "Недостаточно товара на складе", "details": f"Запрошено: {request.quantity}, доступно: {product.quantity}"})
    existing_item = db.query(OrderItem).filter(OrderItem.order_id == request.order_id, OrderItem.product_id == request.product_id).first()
    if existing_item:
        new_total_quantity = existing_item.quantity + request.quantity
        if product.quantity < new_total_quantity:
            raise HTTPException(status_code=409, detail={"success": False, "error": "Недостаточно товара на складе",
                "details": f"В заказе уже {existing_item.quantity} шт. Запрошено добавить: {request.quantity} шт. Всего потребуется: {new_total_quantity} шт. Доступно: {product.quantity} шт."})
        existing_item.quantity = new_total_quantity
        order_item_id = existing_item.id
        total_quantity = new_total_quantity
        message = f"Количество товара '{product.name}' в заказе увеличено на {request.quantity} шт."
    else:
        new_item = OrderItem(order_id=request.order_id, product_id=request.product_id, quantity=request.quantity, price=product.price)
        db.add(new_item)
        db.flush()
        order_item_id = new_item.id
        total_quantity = request.quantity
        message = f"Товар '{product.name}' добавлен в заказ в количестве {request.quantity} шт."
    product.quantity -= request.quantity
    product.updated_at = datetime.utcnow()
    db.commit()
    update_order_total(db, request.order_id)
    updated_order = db.query(Order).filter(Order.id == request.order_id).first()
    return AddItemResponse(success=True, message=message, order_item_id=order_item_id, total_quantity=total_quantity, order_total=float(updated_order.total_amount))

@app.get("/orders/{order_id}", summary="Получить информацию о заказе")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return {
        "order": {
            "id": order.id,
            "client_id": order.client_id,
            "status": order.status,
            "total_amount": float(order.total_amount),
            "order_date": order.order_date
        },
        "items": [{
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "price": float(item.price),
            "total": float(item.quantity * item.price)
        } for item in order.order_items]
    }

@app.get("/products/{product_id}", summary="Получить информацию о товаре")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "quantity": product.quantity,
        "category": product.category.name if product.category else None
    }

@app.get("/", summary="Корневой эндпоинт")
def root():
    return {
        "message": "Order Management API - Тестовое задание Python Developer",
        "version": "1.0.0",
        "endpoints": {
            "add_item": "POST /orders/add-item",
            "get_order": "GET /orders/{order_id}",
            "get_product": "GET /products/{product_id}",
            "docs": "GET /docs",
            "redoc": "GET /redoc"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


