# H_R Project1 - AI 쇼핑몰 서비스

Flask와 MySQL을 기반으로 구현한 의류 쇼핑몰 웹 서비스입니다. 기본적인 상품 조회, 검색, 회원가입/로그인, 장바구니, 주문 흐름을 제공하며, 리뷰 데이터를 활용한 체형 기반 사이즈 추천 기능과 CLIP 이미지 임베딩 기반 유사 상품 검색 기능을 포함합니다.

## 프로젝트 개요

본 프로젝트는 온라인 쇼핑몰에서 사용자가 상품을 탐색하고 구매하는 흐름을 구현한 웹 애플리케이션입니다. 단순 상품 목록 제공에 그치지 않고, 사용자의 키, 몸무게, 성별, 선호 핏과 다른 사용자들의 리뷰 데이터를 비교하여 적절한 사이즈를 추천합니다. 또한 상품 이미지를 임베딩하여 사용자가 업로드한 이미지와 유사한 상품을 검색할 수 있도록 구성했습니다.

## 주요 기능

- 회원가입 및 로그인/로그아웃
- 상품 목록 조회 및 카테고리별 필터링
- 상품명/브랜드명 기반 키워드 검색
- 상품 상세 페이지 제공
- 장바구니 담기, 수량 변경, 삭제
- 주문 페이지 및 주문 완료 처리
- 구매 리뷰 작성 및 조회
- 사용자 체형/선호 핏 기반 사이즈 추천
- CLIP 이미지 임베딩 기반 유사 상품 검색
- 데모 사용자, 상품, 리뷰 데이터 초기화 기능

## 핵심 기능 설명

### 1. 쇼핑몰 기본 기능

Flask 라우팅을 통해 메인 페이지, 로그인, 회원가입, 상품 상세, 장바구니, 주문, 주문 완료 페이지를 구성했습니다. 상품 데이터는 MySQL에 저장하며, PyMySQL을 사용해 서버와 데이터베이스를 연동했습니다.

### 2. 체형 기반 사이즈 추천

사용자의 성별, 키, 몸무게, 선호 핏 정보를 기준으로 유사한 체형의 리뷰 데이터를 검색합니다. 유사 사용자가 실제 구매한 사이즈, 사이즈 체감, 핏 체감, 평점, 리뷰 키워드를 집계하여 추천 사이즈와 추천 근거를 제공합니다.

추천 기준 예시:

- 동일 성별 사용자
- 키 차이 ±3cm 이내
- 몸무게 차이 ±5kg 이내
- 동일한 선호 핏
- 유사 사용자 리뷰의 구매 사이즈 최빈값
- 리뷰 평점 및 키워드 기반 보조 설명

### 3. 이미지 기반 유사 상품 검색

OpenAI CLIP 모델의 `ViT-B/32` 이미지 인코더를 사용하여 상품 이미지를 벡터로 변환합니다. 사용자가 이미지를 업로드하면 동일한 방식으로 쿼리 이미지를 임베딩하고, 기존 상품 임베딩과 cosine similarity를 계산하여 유사도가 높은 상품을 반환합니다.

이미지 검색 흐름:

```text
상품 이미지 수집
        ↓
CLIP 이미지 임베딩 생성
        ↓
embeddings.pkl 저장
        ↓
사용자 이미지 업로드
        ↓
쿼리 이미지 임베딩 생성
        ↓
Cosine Similarity 기반 Top-k 상품 검색
```

## 사용 기술

- Python
- Flask
- MySQL
- PyMySQL
- HTML/CSS
- Jinja2 Template
- PyTorch
- CLIP
- Pillow
- scikit-learn
- NumPy

## 폴더 구조

```text
H_R_Project1-main/
├── README.md
├── H_R_Project1-shopmall/
│   ├── project1/
│   │   ├── app.py                  # 기본 쇼핑몰 서버 및 추천 기능
│   │   ├── recommendation.py       # 체형/리뷰 기반 사이즈 추천 로직
│   │   ├── search.py               # 이미지 유사도 검색 로직
│   │   ├── make_pkl.py             # 상품 이미지 임베딩 생성 스크립트
│   │   ├── schema.sql              # DB 스키마
│   │   ├── requirements.txt        # 기본 실행 패키지
│   │   ├── embeddings.pkl          # 이미지 임베딩 데이터
│   │   ├── templates/              # HTML 템플릿
│   │   └── static/                 # 정적 파일 및 업로드 이미지
│   │
│   ├── project_insu/
│   │   ├── app.py                  # 상품 DB view 연동 확장 버전
│   │   ├── recommendation.py
│   │   ├── search.py
│   │   ├── make_pkl.py
│   │   ├── schema.sql
│   │   ├── embeddings.pkl
│   │   ├── templates/
│   │   └── static/
│   │
│   └── ys_mypage/
│       └── project1/
│           ├── app.py
│           ├── recommendation.py
│           ├── search.py
│           ├── make_pkl.py
│           ├── schema.sql
│           ├── requirements.txt
│           ├── templates/
│           └── static/
└── hello.txt
```

## 설치 및 실행 방법

### 1. 프로젝트 다운로드

```bash
git clone <repository-url>
cd H_R_Project1-main/H_R_Project1-shopmall/project1
```

또는 zip 파일을 다운로드한 뒤 압축을 해제하고 `project1` 폴더로 이동합니다.

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
```

Windows PowerShell:

```bash
.\venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

이미지 검색 기능까지 실행하려면 아래 패키지도 필요합니다.

```bash
pip install torch torchvision pillow scikit-learn numpy git+https://github.com/openai/CLIP.git
```

### 4. MySQL 데이터베이스 생성

MySQL에 접속한 뒤 `schema.sql`을 실행합니다.

```bash
mysql -u root -p < schema.sql
```

`schema.sql`에는 다음 테이블이 포함되어 있습니다.

- `users`: 회원 정보
- `products`: 상품 정보
- `reviews`: 상품 리뷰 정보

### 5. DB 연결 설정

`app.py`와 관련 모듈은 `db.py`의 `get_connection()` 함수를 통해 MySQL에 연결하는 구조입니다. 실행 전 로컬 환경에 맞게 DB 접속 정보를 설정해야 합니다.

예시:

```python
import pymysql


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="your_password",
        db="shoppingmall",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
```

`project_insu` 버전은 상품 정보를 별도 DB 또는 view인 `products_for_shop`에서 조회하므로, `get_product_connection()` 함수도 함께 구성해야 합니다.

### 6. 서버 실행

```bash
python app.py
```

브라우저에서 접속합니다.

```text
http://127.0.0.1:5000
```

## 데모 데이터 초기화

서버 실행 후 아래 주소에 접속하면 데모 사용자, 상품, 리뷰 데이터가 삽입됩니다.

```text
http://127.0.0.1:5000/init-demo
```

데모 로그인 예시:

```text
ID: insu
PW: 1234
```

## 이미지 검색 임베딩 생성

상품 이미지 데이터가 변경되었거나 `embeddings.pkl`을 새로 만들고 싶다면 아래 명령을 실행합니다.

```bash
python make_pkl.py
```

생성 결과:

```text
embeddings.pkl
```

이 파일은 상품 이미지 임베딩과 상품 메타데이터를 저장하며, `search.py`에서 유사 상품 검색 시 사용됩니다.

## 주요 라우트

| URL | Method | 설명 |
|---|---:|---|
| `/` | GET | 메인 페이지로 이동 |
| `/main` | GET/POST | 상품 목록, 검색, 이미지 검색 |
| `/login` | GET/POST | 로그인 |
| `/logout` | GET | 로그아웃 |
| `/signup` | GET/POST | 회원가입 |
| `/product/<p_id>` | GET | 상품 상세 및 추천 결과 조회 |
| `/review/create/<product_id>` | GET/POST | 리뷰 작성 |
| `/add_cart/<p_id>` | GET | 장바구니 추가 |
| `/update_cart/<p_id>/<action>` | GET | 장바구니 수량 변경/삭제 |
| `/cart` | GET | 장바구니 조회 |
| `/order` | GET | 주문 페이지 |
| `/order_complete` | GET | 주문 완료 |
| `/init-demo` | GET | 데모 데이터 초기화 |

## 데이터베이스 구조

### users

| 컬럼 | 설명 |
|---|---|
| `user_id` | 사용자 고유 ID |
| `username` | 로그인 ID |
| `password` | 비밀번호 |
| `gender` | 성별 |
| `height` | 키 |
| `weight` | 몸무게 |
| `preferred_fit` | 선호 핏 |
| `usual_size` | 평소 사이즈 |
| `created_at` | 가입 일시 |

### products

| 컬럼 | 설명 |
|---|---|
| `product_id` | 상품 고유 ID |
| `product_name` | 상품명 |
| `brand` | 브랜드명 |
| `category` | 카테고리 |
| `price` | 가격 |
| `size_options` | 제공 사이즈 |
| `created_at` | 등록 일시 |

### reviews

| 컬럼 | 설명 |
|---|---|
| `review_id` | 리뷰 고유 ID |
| `user_id` | 작성자 ID |
| `product_id` | 상품 ID |
| `purchased_size` | 구매 사이즈 |
| `size_feel` | 사이즈 체감 |
| `fit_feel` | 핏 체감 |
| `rating` | 평점 |
| `review_text` | 리뷰 내용 |
| `created_at` | 작성 일시 |

## 추천 로직 요약

1. 로그인한 사용자의 체형 정보와 선호 핏을 조회합니다.
2. 같은 상품을 구매한 리뷰 중 유사 체형 사용자의 리뷰를 검색합니다.
3. 유사 사용자의 구매 사이즈 분포를 계산합니다.
4. 가장 많이 선택된 사이즈를 추천 사이즈로 선정합니다.
5. 평균 평점, 사이즈 체감, 핏 체감, 리뷰 키워드를 함께 제공하여 추천 근거를 설명합니다.

## 이미지 검색 로직 요약

1. 상품 이미지를 CLIP 모델로 임베딩합니다.
2. 임베딩 결과를 `embeddings.pkl`에 저장합니다.
3. 사용자가 업로드한 이미지를 동일한 CLIP 모델로 임베딩합니다.
4. 저장된 상품 임베딩과 cosine similarity를 계산합니다.
5. 유사도가 높은 Top-k 상품을 검색 결과로 반환합니다.

## 포트폴리오 요약 문장

Flask와 MySQL 기반 의류 쇼핑몰 웹 서비스를 구현하고, 사용자 체형·선호 핏·리뷰 데이터를 활용한 사이즈 추천 기능과 CLIP 이미지 임베딩 기반 유사 상품 검색 기능을 개발했습니다. 상품 탐색, 회원 관리, 리뷰, 장바구니, 주문 흐름을 통합하여 실제 쇼핑몰 서비스와 유사한 사용자 경험을 제공하도록 구성했습니다.

## 참고 사항

- 기본 `requirements.txt`에는 Flask와 PyMySQL만 포함되어 있으므로 이미지 검색 기능을 사용할 경우 PyTorch, CLIP, Pillow, scikit-learn, NumPy를 추가로 설치해야 합니다.
- `embeddings.pkl`은 이미지 검색에 필요한 임베딩 파일입니다.
- `project_insu` 버전은 `shoppingmall3.products` 테이블과 `products_for_shop` view를 사용하는 확장 구조입니다.
- 개발용 예제이므로 실제 서비스 적용 시 비밀번호 해싱, 입력값 검증, 세션 보안, SQL 권한 관리 등을 보완해야 합니다.
