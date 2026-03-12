DROP DATABASE IF EXISTS shoppingmall3;
CREATE DATABASE shoppingmall3 CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE shoppingmall3;

SET FOREIGN_KEY_CHECKS = 0;

-- =========================================
-- 1. accounts
-- =========================================
CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    login_id VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('seller', 'customer', 'admin') NOT NULL DEFAULT 'seller',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- 2. sellers
-- =========================================
CREATE TABLE sellers (
    seller_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NULL UNIQUE,
    seller_name VARCHAR(100) NOT NULL,
    brand_name VARCHAR(50) NULL,
    email VARCHAR(100),
    phone VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sellers_account
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        ON DELETE SET NULL
);

-- =========================================
-- 3. products
-- app.py 기준 컬럼 구조
-- =========================================
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL,

    product_code VARCHAR(20) NOT NULL UNIQUE,
    brand_name VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,

    category1 VARCHAR(100) NOT NULL,
    category2 VARCHAR(100) NOT NULL,

    gender ENUM('남성', '여성', '공용') NOT NULL DEFAULT '공용',

    price INT NOT NULL DEFAULT 0,
    color VARCHAR(50),
    size VARCHAR(20),
    stock INT NOT NULL DEFAULT 0,

    status ENUM('판매중', '품절', '숨김') NOT NULL DEFAULT '판매중',

    description TEXT,

    image_main1 VARCHAR(255) NOT NULL,
    image_main2 VARCHAR(255),
    image_main3 VARCHAR(255),
    image_detail VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_products_seller
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        ON DELETE CASCADE
);

-- =========================================
-- 4. orders (user_id: 고객 쇼핑몰 연동)
-- =========================================
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_code VARCHAR(30) NOT NULL UNIQUE,
    seller_id INT NOT NULL,
    user_id INT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(30),
    customer_email VARCHAR(100),
    address VARCHAR(255),
    order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount INT NOT NULL DEFAULT 0,
    order_status ENUM('신규주문', '배송준비중', '배송중', '배송완료', '반품요청', '교환요청') DEFAULT '신규주문',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_orders_seller
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        ON DELETE CASCADE
);

-- =========================================
-- 5. order_items
-- =========================================
CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,

    quantity INT NOT NULL DEFAULT 1,
    unit_price INT NOT NULL DEFAULT 0,
    subtotal INT NOT NULL DEFAULT 0,

    selected_size VARCHAR(20),
    selected_color VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON DELETE CASCADE
);

-- =========================================
-- 6. 문의 / 교환 / 반품 테이블
-- =========================================
CREATE TABLE customer_service (
    cs_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    seller_id INT NOT NULL,
    customer_name VARCHAR(100),
    cs_type ENUM('상품문의','교환요청','반품요청') NOT NULL,
    cs_title VARCHAR(200),
    cs_content TEXT,
    cs_reply TEXT,
    cs_status ENUM('접수','처리중','처리완료') DEFAULT '접수',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id) ON DELETE CASCADE
);

-- =========================================
-- 7. 판매자 계정 5개
-- =========================================
INSERT INTO accounts (login_id, password, role, is_active) VALUES
('nike', '1234', 'seller', 1),
('matinkim', '1234', 'seller', 1),
('newbalance', '1234', 'seller', 1),
('puma', '1234', 'seller', 1),
('fila', '1234', 'seller', 1);

-- =========================================
-- 8. 판매자 5명
-- =========================================
INSERT INTO sellers (account_id, seller_name, brand_name, email, phone) VALUES
(1, '나이키 판매자', '나이키', 'nike@seller.com', '010-1111-1111'),
(2, '마뗑킴 판매자', '마뗑킴', 'matinkim@seller.com', '010-2222-2222'),
(3, '뉴발란스 판매자', '뉴발란스', 'newbalance@seller.com', '010-3333-3333'),
(4, '푸마 판매자', '푸마', 'puma@seller.com', '010-4444-4444'),
(5, 'FILA 판매자', 'FILA', 'fila@seller.com', '010-5555-5555');

-- =========================================
-- 9. 상품 샘플 데이터
-- 현재 products 구조에 맞게 수정
-- =========================================
INSERT INTO products (
    seller_id,
    product_code,
    brand_name,
    product_name,
    category1,
    category2,
    gender,
    price,
    color,
    size,
    stock,
    status,
    description,
    image_main1,
    image_main2,
    image_main3,
    image_detail
) VALUES

-- 나이키
(1, 'P001', '나이키', '나이키 써마 핏 트레이닝 팬츠', '하의', '트레이닝팬츠', '남성', 68850, '블랙', 'S', 10, '판매중',
'부드럽고 따뜻한 소재로 제작된 나이키 트레이닝 팬츠입니다. 운동과 일상 모두 활용 가능합니다.',
'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600',
'https://images.unsplash.com/photo-1506629905607-d9d0b1b38f08?w=600',
'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600'),

(1, 'P002', '나이키', '나이키 드라이핏 반팔 티셔츠', '상의', '반팔티', '남성', 42000, '화이트', 'M', 15, '판매중',
'땀 배출이 빠른 드라이핏 기능성 반팔 티셔츠입니다.',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600'),

(1, 'P003', '나이키', '나이키 러닝 쇼츠 5인치', '하의', '쇼츠', '여성', 48000, '네이비', 'M', 4, '판매중',
'가볍고 시원한 착용감의 러닝용 쇼츠입니다.',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600',
'https://images.unsplash.com/photo-1506629905607-d9d0b1b38f08?w=600',
'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600',
'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600'),

(1, 'P004', '나이키', '나이키 에어 러닝화', '신발', '러닝화', '공용', 119000, '레드', '260', 0, '품절',
'쿠셔닝이 우수한 러닝화로 일상 러닝과 워킹에 적합합니다.',
'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600',
'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600',
'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=600',
'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=600'),

(1, 'P005', '나이키', '나이키 후드 집업', '아우터', '후드집업', '공용', 89000, '그레이', 'L', 6, '숨김',
'간절기에 활용하기 좋은 후드 집업입니다.',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600'),

-- 마뗑킴
(2, 'P006', '마뗑킴', '마뗑킴 클래식 로고 후드', '상의', '후드티', '공용', 98000, '크림', 'FREE', 7, '판매중',
'마뗑킴 감성의 오버핏 로고 후드티입니다.',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600'),

(2, 'P007', '마뗑킴', '마뗑킴 미니 숄더백', '잡화', '숄더백', '여성', 128000, '블랙', 'FREE', 5, '판매중',
'데일리 룩에 매치하기 좋은 미니 숄더백입니다.',
'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600',
'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600',
'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=600',
'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=600'),

(2, 'P008', '마뗑킴', '마뗑킴 오버핏 자켓', '아우터', '자켓', '여성', 159000, '카키', 'M', 3, '판매중',
'루즈한 실루엣이 특징인 마뗑킴 자켓입니다.',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600'),

(2, 'P009', '마뗑킴', '마뗑킴 크롭 니트', '상의', '니트', '여성', 87000, '핑크', 'S', 0, '품절',
'트렌디한 크롭 기장의 니트 상의입니다.',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600'),

(2, 'P010', '마뗑킴', '마뗑킴 와이드 데님 팬츠', '하의', '데님팬츠', '공용', 109000, '블루', 'L', 9, '판매중',
'여유로운 실루엣의 와이드 데님 팬츠입니다.',
'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600',
'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600',
'https://images.unsplash.com/photo-1506629905607-d9d0b1b38f08?w=600',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600'),

-- 뉴발란스
(3, 'P011', '뉴발란스', '뉴발란스 530 스니커즈', '신발', '스니커즈', '공용', 129000, '화이트', '250', 12, '판매중',
'편안한 착화감으로 인기 있는 뉴발란스 대표 스니커즈입니다.',
'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600',
'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=600',
'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=600',
'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600'),

(3, 'P012', '뉴발란스', '뉴발란스 조거 팬츠', '하의', '조거팬츠', '남성', 69000, '그레이', 'M', 8, '판매중',
'데일리하게 착용 가능한 조거 팬츠입니다.',
'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600',
'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600',
'https://images.unsplash.com/photo-1506629905607-d9d0b1b38f08?w=600',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600'),

(3, 'P013', '뉴발란스', '뉴발란스 후드티', '상의', '후드티', '공용', 79000, '네이비', 'L', 11, '판매중',
'캐주얼한 무드의 기본 후드티입니다.',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600'),

(3, 'P014', '뉴발란스', '뉴발란스 러닝 반팔티', '상의', '반팔티', '여성', 45000, '블랙', 'S', 0, '품절',
'통기성이 뛰어난 러닝 반팔티입니다.',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600'),

(3, 'P015', '뉴발란스', '뉴발란스 플리스 집업', '아우터', '플리스집업', '공용', 99000, '베이지', 'M', 4, '판매중',
'보온성이 좋은 플리스 소재 집업입니다.',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600'),

-- 푸마
(4, 'P016', '푸마', '푸마 베이직 반팔티', '상의', '반팔티', '남성', 35000, '화이트', 'M', 14, '판매중',
'심플한 디자인의 푸마 베이직 반팔티입니다.',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600'),

(4, 'P017', '푸마', '푸마 트랙 팬츠', '하의', '트랙팬츠', '남성', 62000, '블랙', 'L', 6, '판매중',
'활동성과 착용감이 우수한 푸마 트랙 팬츠입니다.',
'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600',
'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600',
'https://images.unsplash.com/photo-1506629905607-d9d0b1b38f08?w=600',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600'),

(4, 'P018', '푸마', '푸마 러닝화', '신발', '러닝화', '공용', 99000, '블루', '260', 5, '판매중',
'경량성과 쿠셔닝을 갖춘 러닝화입니다.',
'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=600',
'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600',
'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=600',
'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600'),

(4, 'P019', '푸마', '푸마 스포츠 후드집업', '아우터', '후드집업', '공용', 85000, '그린', 'XL', 0, '품절',
'운동 전후 걸치기 좋은 푸마 후드집업입니다.',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600'),

(4, 'P020', '푸마', '푸마 로고 맨투맨', '상의', '맨투맨', '공용', 58000, '네이비', 'M', 7, '숨김',
'심플한 로고 포인트의 맨투맨입니다.',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600'),

-- FILA
(5, 'P021', 'FILA', 'FILA 디스럽터 스니커즈', '신발', '스니커즈', '공용', 89000, '화이트', '240', 9, '판매중',
'볼드한 실루엣이 특징인 FILA 대표 스니커즈입니다.',
'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=600',
'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600',
'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=600',
'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600'),

(5, 'P022', 'FILA', 'FILA 클래식 맨투맨', '상의', '맨투맨', '공용', 52000, '레드', 'L', 10, '판매중',
'캐주얼하게 입기 좋은 FILA 클래식 맨투맨입니다.',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600'),

(5, 'P023', 'FILA', 'FILA 와이드 팬츠', '하의', '와이드팬츠', '여성', 61000, '그레이', 'S', 3, '판매중',
'편안한 핏의 와이드 팬츠로 데일리 착용에 적합합니다.',
'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600',
'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600',
'https://images.unsplash.com/photo-1506629905607-d9d0b1b38f08?w=600',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600'),

(5, 'P024', 'FILA', 'FILA 반팔 로고 티셔츠', '상의', '반팔티', '공용', 39000, '블랙', 'M', 0, '품절',
'심플한 로고 포인트의 기본 반팔 티셔츠입니다.',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600'),

(5, 'P025', 'FILA', 'FILA 집업 트랙 자켓', '아우터', '트랙자켓', '공용', 76000, '네이비', 'L', 5, '판매중',
'스포티한 분위기의 집업 트랙 자켓입니다.',
'https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600',
'https://images.unsplash.com/photo-1523398002811-999ca8dec234?w=600',
'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600',
'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600');

-- =========================================
-- 9. 주문 샘플
-- =========================================
INSERT INTO orders (
    order_code, seller_id, customer_name, customer_phone, customer_email, address,
    order_date, total_amount, order_status
) VALUES
('ORDER001', 1, '김민수', '010-9001-0001', 'kim1@test.com', '서울시 강남구 테헤란로 101', NOW(), 137700, '배송준비중'),
('ORDER002', 1, '박지은', '010-9001-0002', 'park2@test.com', '서울시 송파구 올림픽로 202', NOW(), 48000, '배송중'),
('ORDER003', 1, '최수진', '010-9001-0003', 'choi3@test.com', '서울시 마포구 월드컵북로 303', DATE_SUB(NOW(), INTERVAL 1 DAY), 119000, '반품요청'),
('ORDER004', 2, '이도윤', '010-9002-0001', 'lee4@test.com', '경기도 성남시 분당구 404', DATE_SUB(NOW(), INTERVAL 1 DAY), 98000, '신규주문'),
('ORDER005', 2, '한예린', '010-9002-0002', 'han5@test.com', '경기도 수원시 영통구 505', DATE_SUB(NOW(), INTERVAL 2 DAY), 128000, '신규주문'),
('ORDER006', 3, '정우성', '010-9003-0001', 'jung6@test.com', '인천시 연수구 센트럴로 606', DATE_SUB(NOW(), INTERVAL 2 DAY), 129000, '배송완료'),
('ORDER007', 3, '윤아름', '010-9003-0002', 'yoon7@test.com', '대전시 서구 둔산로 707', DATE_SUB(NOW(), INTERVAL 3 DAY), 138000, '배송완료'),
('ORDER008', 4, '서하준', '010-9004-0001', 'seo8@test.com', '광주시 북구 용봉로 808', DATE_SUB(NOW(), INTERVAL 3 DAY), 99000, '배송준비중'),
('ORDER009', 4, '강도현', '010-9004-0002', 'kang9@test.com', '부산시 해운대구 센텀로 909', DATE_SUB(NOW(), INTERVAL 4 DAY), 62000, '교환요청'),
('ORDER010', 5, '유지민', '010-9005-0001', 'yoo10@test.com', '대구시 수성구 달구벌대로 1001', DATE_SUB(NOW(), INTERVAL 4 DAY), 89000, '배송완료'),
('ORDER011', 5, '오세은', '010-9005-0002', 'oh11@test.com', '울산시 남구 삼산로 1102', DATE_SUB(NOW(), INTERVAL 5 DAY), 113000, '배송중'),
('ORDER012', 1, '문가영', '010-9001-0004', 'moon12@test.com', '서울시 강서구 공항대로 1203', DATE_SUB(NOW(), INTERVAL 6 DAY), 84000, '배송완료');

-- =========================================
-- 10. 주문 상세 샘플
-- =========================================
INSERT INTO order_items (
    order_id, product_id, quantity, unit_price, subtotal, selected_size, selected_color
) VALUES
(1, 1, 2, 68850, 137700, 'S', '블랙'),
(2, 3, 1, 48000, 48000, 'M', '네이비'),
(3, 4, 1, 119000, 119000, '260', '레드'),
(4, 6, 1, 98000, 98000, 'FREE', '크림'),
(5, 7, 1, 128000, 128000, 'FREE', '블랙'),
(6, 11, 1, 129000, 129000, '250', '화이트'),
(7, 12, 2, 69000, 138000, 'M', '그레이'),
(8, 18, 1, 99000, 99000, '260', '블루'),
(9, 17, 1, 62000, 62000, 'L', '블랙'),
(10, 21, 1, 89000, 89000, '240', '화이트'),
(11, 22, 1, 52000, 52000, 'L', '레드'),
(11, 23, 1, 61000, 61000, 'S', '그레이'),
(12, 2, 2, 42000, 84000, 'M', '화이트');

-- =========================================
-- 13. 고객 회원 테이블 (쇼핑몰용)
-- =========================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    gender VARCHAR(10),
    height INT,
    weight INT,
    preferred_fit VARCHAR(20),
    usual_size VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- 14. 상품 리뷰 테이블
-- =========================================
CREATE TABLE reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    purchased_size VARCHAR(10) NOT NULL,
    size_feel VARCHAR(20),
    fit_feel VARCHAR(20),
    rating INT,
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- =========================================
-- 15. 데모 고객 유저
-- =========================================
INSERT INTO users (username, password, gender, height, weight, preferred_fit, usual_size) VALUES
('insu', '1234', '남', 173, 68, '세미오버핏', 'M'),
('minho', '1234', '남', 172, 67, '세미오버핏', 'M'),
('jinho', '1234', '남', 174, 70, '세미오버핏', 'M'),
('hyun', '1234', '남', 173, 66, '세미오버핏', 'M'),
('taeho', '1234', '남', 173, 68, '세미오버핏', 'M'),
('jun', '1234', '남', 172, 65, '세미오버핏', 'M'),
('woojin', '1234', '남', 176, 72, '오버핏', 'L'),
('seong', '1234', '남', 170, 64, '정핏', 'S'),
('yong', '1234', '남', 174, 68, '세미오버핏', 'M'),
('dong', '1234', '남', 172, 67, '세미오버핏', 'M'),
('jiwon', '1234', '여', 162, 52, '오버핏', 'L'),
('hojun', '1234', '남', 178, 75, '오버핏', 'L'),
('minseok', '1234', '남', 173, 69, '세미오버핏', 'M');

SET FOREIGN_KEY_CHECKS = 1;