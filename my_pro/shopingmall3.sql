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
-- 4. orders
-- =========================================
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_code VARCHAR(30) NOT NULL UNIQUE,
    seller_id INT NOT NULL,
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
-- 7. customer_service 데이터 
-- =========================================
INSERT INTO customer_service
(order_id, product_id, seller_id, customer_name, cs_type, cs_title, cs_content, cs_status)
VALUES
(27, 4, 1, '최수진', '반품요청', '사이즈 문제', '사이즈가 맞지 않아 반품 요청합니다.', '접수'),

(33, 17, 1, '강도현', '교환요청', '색상 교환', '블랙 대신 네이비로 교환하고 싶습니다.', '접수'),

(25, 1, 1, '김민수', '상품문의', '세탁 방법', '이 제품 세탁기 사용 가능한가요?', '접수');

(25, 1, 1, '김민수', '상품문의', '사이즈 문의', '이 제품 M 사이즈 있나요?', '접수'),

(26, 2, 1, '박지은', '상품문의', '배송 문의', '오늘 주문하면 언제 도착하나요?', '접수'),

(27, 3, 1, '이도현', '상품문의', '재입고 문의', '품절인데 재입고 예정 있나요?', '처리중'),

(28, 4, 1, '최수진', '상품문의', '색상 문의', '블랙 말고 다른 색상 있나요?', '처리완료'),

(29, 5, 1, '강도현', '상품문의', '세탁 방법', '세탁기 사용 가능한가요?', '접수');
(30, 6, 1, '정유진', '교환요청', '사이즈가 맞지 않아 L로 교환 요청합니다.', '접수'),

(31, 7, 1, '한지민', '교환요청', '색상을 블랙으로 교환하고 싶습니다.', '처리중'),

(32, 8, 1, '윤태준', '교환요청', '상품이 너무 작아서 교환 요청합니다.', '처리완료');
(33, 9, 1, '송하늘', '반품요청', '제품이 생각보다 커서 반품 요청합니다.', '접수'),

(34, 10, 1, '김서연', '반품요청', '배송 중 파손되어 반품합니다.', '처리중'),

(35, 11, 1, '박준영', '반품요청', '상품 불량으로 반품 요청합니다.', '처리완료');

-- =========================================
-- 8. 판매자 계정 5개
-- =========================================
INSERT INTO accounts (login_id, password, role, is_active) VALUES
('nike', '1234', 'seller', 1),
('matinkim', '1234', 'seller', 1),
('newbalance', '1234', 'seller', 1),
('puma', '1234', 'seller', 1),
('fila', '1234', 'seller', 1);

-- =========================================
-- 9. 판매자 5명
-- =========================================
INSERT INTO sellers (account_id, seller_name, brand_name, email, phone) VALUES
(1, '나이키 판매자', '나이키', 'nike@seller.com', '010-1111-1111'),
(2, '마뗑킴 판매자', '마뗑킴', 'matinkim@seller.com', '010-2222-2222'),
(3, '뉴발란스 판매자', '뉴발란스', 'newbalance@seller.com', '010-3333-3333'),
(4, '푸마 판매자', '푸마', 'puma@seller.com', '010-4444-4444'),
(5, 'FILA 판매자', 'FILA', 'fila@seller.com', '010-5555-5555');

-- =========================================
-- 10. 상품 샘플 데이터
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
-- 11. 주문 샘플
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
-- 12. 주문 상세 샘플
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

SET FOREIGN_KEY_CHECKS = 1;




-- =========================================
-- 13. 주문 추가 데이터 
-- =========================================
INSERT INTO orders (order_code, seller_id, customer_name, customer_phone, address, order_date, total_amount) VALUES
('ORD2001',1,'김민수','010-1000-0001','서울','2024-01-05',54000),
('ORD2002',1,'박지은','010-1000-0002','서울','2024-01-11',89000),
('ORD2003',1,'최수진','010-1000-0003','서울','2024-02-03',72000),
('ORD2004',1,'이동윤','010-1000-0004','서울','2024-02-18',99000),
('ORD2005',1,'한예린','010-1000-0005','서울','2024-03-01',65000),
('ORD2006',1,'정우성','010-1000-0006','서울','2024-03-15',123000),
('ORD2007',1,'윤아름','010-1000-0007','서울','2024-04-02',78000),
('ORD2008',1,'서하준','010-1000-0008','서울','2024-04-20',87000),
('ORD2009',1,'강도현','010-1000-0009','서울','2024-05-09',111000),
('ORD2010',1,'유지민','010-1000-0010','서울','2024-05-27',56000),

('ORD2011',1,'오세훈','010-1000-0011','서울','2024-06-05',91000),
('ORD2012',1,'문가영','010-1000-0012','서울','2024-06-22',74000),
('ORD2013',1,'김철수','010-1000-0013','서울','2024-07-02',98000),
('ORD2014',1,'이영희','010-1000-0014','서울','2024-07-15',134000),
('ORD2015',1,'박민수','010-1000-0015','서울','2024-08-03',45000),
('ORD2016',1,'정다은','010-1000-0016','서울','2024-08-21',167000),
('ORD2017',1,'김태훈','010-1000-0017','서울','2024-09-10',88000),
('ORD2018',1,'이동욱','010-1000-0018','서울','2024-09-25',92000),
('ORD2019',1,'박소연','010-1000-0019','서울','2024-10-01',67000),
('ORD2020',1,'강민재','010-1000-0020','서울','2024-10-17',140000),

('ORD2021',1,'김영수','010-1000-0021','서울','2024-11-04',82000),
('ORD2022',1,'정민지','010-1000-0022','서울','2024-11-22',93000),
('ORD2023',1,'이서연','010-1000-0023','서울','2024-12-01',112000),
('ORD2024',1,'박지수','010-1000-0024','서울','2024-12-24',189000),

('ORD2025',1,'최유리','010-1000-0025','서울','2025-01-03',78000),
('ORD2026',1,'김도윤','010-1000-0026','서울','2025-01-15',99000),
('ORD2027',1,'이하늘','010-1000-0027','서울','2025-02-01',84000),
('ORD2028',1,'강지훈','010-1000-0028','서울','2025-02-19',91000),
('ORD2029',1,'홍길동','010-1000-0029','서울','2025-03-05',120000),
('ORD2030',1,'박성민','010-1000-0030','서울','2025-03-18',76000),

('ORD2031',1,'윤서진','010-1000-0031','서울','2025-04-02',54000),
('ORD2032',1,'김하은','010-1000-0032','서울','2025-04-19',83000),
('ORD2033',1,'이재훈','010-1000-0033','서울','2025-05-03',99000),
('ORD2034',1,'최지우','010-1000-0034','서울','2025-05-27',67000),
('ORD2035',1,'강민석','010-1000-0035','서울','2025-06-10',91000),
('ORD2036',1,'김지수','010-1000-0036','서울','2025-06-22',74000),

('ORD2037',1,'박민지','010-1000-0037','서울','2025-07-05',125000),
('ORD2038',1,'이준호','010-1000-0038','서울','2025-07-21',88000),
('ORD2039',1,'정다윤','010-1000-0039','서울','2025-08-11',96000),
('ORD2040',1,'김태리','010-1000-0040','서울','2025-08-28',131000),

('ORD2041',1,'한지민','010-1000-0041','서울','2025-09-03',87000),
('ORD2042',1,'박보검','010-1000-0042','서울','2025-09-19',92000),
('ORD2043',1,'손예진','010-1000-0043','서울','2025-10-06',145000),
('ORD2044',1,'현빈','010-1000-0044','서울','2025-10-24',83000),

('ORD2045',1,'전지현','010-1000-0045','서울','2025-11-02',92000),
('ORD2046',1,'송중기','010-1000-0046','서울','2025-11-18',88000),
('ORD2047',1,'김수현','010-1000-0047','서울','2025-12-04',110000),
('ORD2048',1,'아이유','010-1000-0048','서울','2025-12-26',210000),

('ORD2049',1,'차은우','010-1000-0049','서울','2026-01-10',96000),
('ORD2050',1,'수지','010-1000-0050','서울','2026-02-14',87000);