
-- Файл инициализации базы данных с тестовыми данными

-- СХЕМА БАЗЫ ДАННЫХ
-- (Код схемы из первого файла)

-- 1. Таблица категорий (дерево с неограниченной вложенностью)
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    level INTEGER NOT NULL DEFAULT 0,
    path VARCHAR(1000),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для категорий
CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_path ON categories(path);
CREATE INDEX IF NOT EXISTS idx_categories_level ON categories(level);

-- 2. Таблица товаров
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    category_id INTEGER REFERENCES categories(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);

-- 3. Таблица клиентов
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    total_amount DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_client_id ON orders(client_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);

-- 5. Таблица позиций заказов
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- Триггеры (упрощенные версии для совместимости)
CREATE OR REPLACE FUNCTION update_order_total()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE orders 
    SET total_amount = (
        SELECT COALESCE(SUM(quantity * price), 0)
        FROM order_items 
        WHERE order_id = COALESCE(NEW.order_id, OLD.order_id)
    ),
    updated_at = CURRENT_TIMESTAMP
    WHERE id = COALESCE(NEW.order_id, OLD.order_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_order_total ON order_items;
CREATE TRIGGER trigger_update_order_total
    AFTER INSERT OR UPDATE OR DELETE ON order_items
    FOR EACH ROW
    EXECUTE FUNCTION update_order_total();

-- ТЕСТОВЫЕ ДАННЫЕ

-- Категории (согласно примеру из задания)
INSERT INTO categories (id, name, parent_id, level, path) VALUES 
(1, 'Бытовая техника', NULL, 0, '1'),
(2, 'Стиральные машины', 1, 1, '1.2'),
(3, 'Холодильники', 1, 1, '1.3'),
(4, 'однокамерные', 3, 2, '1.3.4'),
(5, 'двухкамерные', 3, 2, '1.3.5'),
(6, 'Телевизоры', 1, 1, '1.6'),
(7, 'Компьютеры', NULL, 0, '7'),
(8, 'Ноутбуки', 7, 1, '7.8'),
(9, '17"', 8, 2, '7.8.9'),
(10, '19"', 8, 2, '7.8.10'),
(11, 'Моноблоки', 7, 1, '7.11');

-- Клиенты
INSERT INTO clients (name, address) VALUES 
('ООО "Техносфера"', 'Москва, ул. Тверская, д. 1'),
('ИП Иванов И.И.', 'СПб, Невский проспект, д. 10'),
('ООО "МегаТех"', 'Екатеринбург, ул. Ленина, д. 25'),
('ИП Петров П.П.', 'Казань, ул. Баумана, д. 5'),
('ООО "ТехноМир"', 'Новосибирск, ул. Красный проспект, д. 15');

-- Товары
INSERT INTO products (name, quantity, price, category_id) VALUES 
-- Бытовая техника
('Стиральная машина LG F1096ND3', 15, 25990.00, 2),
('Стиральная машина Samsung WF60F4E0W0W', 12, 22500.00, 2),
('Холодильник Atlant МХМ 2835-90', 8, 18990.00, 4),
('Холодильник Bosch KGN39VI25R', 5, 45990.00, 5),
('Холодильник Samsung RS57K4000SA', 3, 67990.00, 5),
('Телевизор LG 43UM7300PLB', 20, 32990.00, 6),
('Телевизор Samsung UE50TU7090U', 18, 41990.00, 6),

-- Компьютеры
('Ноутбук ASUS X543MA-GQ1226T 15.6"', 25, 28990.00, 8),
('Ноутбук HP 17-by4000ur', 12, 42990.00, 9),
('Ноутбук Dell Inspiron 17 3793', 8, 55990.00, 9),
('Моноблок ASUS V241FAK-BA040T', 10, 48990.00, 11),
('Ноутбук Lenovo ThinkPad E15 19"', 6, 75990.00, 10);

-- Заказы (за разные периоды для тестирования отчетов)
INSERT INTO orders (client_id, order_date, status) VALUES 
(1, CURRENT_DATE - INTERVAL '5 days', 'confirmed'),
(2, CURRENT_DATE - INTERVAL '10 days', 'delivered'),
(3, CURRENT_DATE - INTERVAL '15 days', 'confirmed'),
(4, CURRENT_DATE - INTERVAL '20 days', 'delivered'),
(1, CURRENT_DATE - INTERVAL '25 days', 'delivered'),
(5, CURRENT_DATE - INTERVAL '3 days', 'pending'),
(2, CURRENT_DATE - INTERVAL '7 days', 'shipped'),
(3, CURRENT_DATE - INTERVAL '12 days', 'delivered');

-- Позиции заказов
INSERT INTO order_items (order_id, product_id, quantity, price) VALUES 
-- Заказ 1
(1, 1, 2, 25990.00),
(1, 6, 1, 32990.00),

-- Заказ 2  
(2, 3, 1, 18990.00),
(2, 8, 3, 28990.00),

-- Заказ 3
(3, 4, 1, 45990.00),
(3, 7, 2, 41990.00),

-- Заказ 4
(4, 2, 1, 22500.00),
(4, 9, 2, 42990.00),

-- Заказ 5
(5, 5, 1, 67990.00),
(5, 11, 1, 48990.00),

-- Заказ 6
(6, 8, 2, 28990.00),
(6, 6, 1, 32990.00),

-- Заказ 7
(7, 12, 1, 75990.00),
(7, 10, 1, 55990.00),

-- Заказ 8
(8, 1, 1, 25990.00),
(8, 3, 2, 18990.00);

-- Обновляем остатки товаров (уменьшаем на проданное количество)
UPDATE products SET quantity = quantity - (
    SELECT COALESCE(SUM(oi.quantity), 0)
    FROM order_items oi 
    WHERE oi.product_id = products.id
);

-- Создаем VIEW для топ товаров
CREATE OR REPLACE VIEW top_5_products_last_month AS
SELECT 
    p.name AS "Наименование товара",
    COALESCE(
        (SELECT name FROM categories WHERE id = CAST(SPLIT_PART(cat.path, '.', 1) AS INTEGER)), 
        'Без категории'
    ) AS "Категория 1-го уровня",
    SUM(oi.quantity) AS "Общее количество проданных штук"
FROM products p
INNER JOIN order_items oi ON p.id = oi.product_id
INNER JOIN orders o ON oi.order_id = o.id
LEFT JOIN categories cat ON p.category_id = cat.id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '1 month'
GROUP BY p.id, p.name, cat.path
ORDER BY SUM(oi.quantity) DESC
LIMIT 5;

-- Проверяем данные
SELECT 'Категории:' as info;
SELECT id, name, parent_id, level, path FROM categories ORDER BY path;

SELECT 'Клиенты:' as info;
SELECT id, name, address FROM clients;

SELECT 'Товары:' as info;
SELECT p.id, p.name, p.quantity, p.price, c.name as category 
FROM products p 
LEFT JOIN categories c ON p.category_id = c.id
ORDER BY p.id;

SELECT 'Заказы с суммами:' as info;  
SELECT o.id, cl.name as client, o.order_date, o.status, o.total_amount
FROM orders o
JOIN clients cl ON o.client_id = cl.id
ORDER BY o.id;
