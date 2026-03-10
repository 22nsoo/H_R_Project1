DROP DATABASE IF EXISTS shoppingmall;
CREATE DATABASE shoppingmall CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE shoppingmall;

CREATE TABLE sellers (
    seller_id INT AUTO_INCREMENT PRIMARY KEY,
    seller_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(50),
    price INT NOT NULL DEFAULT 0,
    stock INT NOT NULL DEFAULT 0,
    status ENUM('판매중', '품절', '숨김') DEFAULT '판매중',
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_seller
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        ON DELETE CASCADE
);

CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_code VARCHAR(30) NOT NULL UNIQUE,
    seller_id INT NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount INT NOT NULL DEFAULT 0,
    order_status ENUM('주문완료', '배송준비중', '배송중', '배송완료', '취소') DEFAULT '주문완료',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_seller
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        ON DELETE CASCADE
);

CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price INT NOT NULL DEFAULT 0,
    subtotal INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON DELETE CASCADE
);

INSERT INTO sellers (seller_name, email)
VALUES
('현주', 'seller1@test.com'),
('민재', 'seller2@test.com');

INSERT INTO products (seller_id, product_name, category, price, stock, status, image_url) VALUES
(1, '써마 핏 피트니스 팬츠 - M', '팬츠', 69000, 5, '판매중', 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=300'),
(1, '스위프트 드라이 밋 미드라이즈 쇼츠 - W', '쇼츠', 72000, 8, '판매중', 'https://images.unsplash.com/photo-1506629905607-d9d0b1b38f08?w=300'),
(1, '쿨링 릴리스 와이드 팬츠', '팬츠', 64000, 3, '판매중', 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=300'),
(1, '에어 드레 팬츠 - M', '팬츠', 79000, 12, '판매중', 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=300'),
(1, '프로 365 5인치 쇼츠 - W', '쇼츠', 48000, 2, '판매중', 'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=300'),
(2, '러닝 퍼포먼스 반팔 티', '상의', 39000, 7, '판매중', 'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=300'),
(2, '트레이닝 조거 팬츠', '팬츠', 59000, 0, '품절', 'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=300');

INSERT INTO orders (order_code, seller_id, customer_name, order_date, total_amount, order_status) VALUES
('ORDER001', 1, '김민수', NOW(), 138000, '배송준비중'),
('ORDER002', 1, '박지은', NOW(), 72000, '배송중'),
('ORDER003', 1, '최수진', DATE_SUB(NOW(), INTERVAL 1 DAY), 128000, '배송완료'),
('ORDER004', 1, '이도윤', DATE_SUB(NOW(), INTERVAL 2 DAY), 69000, '배송완료'),
('ORDER005', 1, '한예린', DATE_SUB(NOW(), INTERVAL 3 DAY), 144000, '주문완료'),
('ORDER006', 1, '정우성', DATE_SUB(NOW(), INTERVAL 4 DAY), 79000, '배송완료'),
('ORDER007', 1, '윤아름', DATE_SUB(NOW(), INTERVAL 5 DAY), 96000, '배송완료'),
('ORDER008', 1, '서하준', DATE_SUB(NOW(), INTERVAL 6 DAY), 64000, '배송완료'),
('ORDER009', 2, '강도현', NOW(), 39000, '주문완료'),
('ORDER010', 2, '유지민', DATE_SUB(NOW(), INTERVAL 1 DAY), 59000, '취소');

INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 2, 69000, 138000),
(2, 2, 1, 72000, 72000),
(3, 3, 2, 64000, 128000),
(4, 1, 1, 69000, 69000),
(5, 2, 2, 72000, 144000),
(6, 4, 1, 79000, 79000),
(7, 5, 2, 48000, 96000),
(8, 3, 1, 64000, 64000),
(9, 6, 1, 39000, 39000),
(10, 7, 1, 59000, 59000);