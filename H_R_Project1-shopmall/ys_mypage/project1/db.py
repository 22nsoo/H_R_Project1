import pymysql

# 기존에 있던 get_connection 함수 (사용자 정보용)
def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='123', # 본인의 비밀번호로 수정
        database='shoppingmall3',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# 에러가 나고 있는 부분: 이 함수를 추가해야 합니다!
def get_product_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='your_password', # 본인의 비밀번호로 수정
        database='shoppingmall3',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def get_all_products():
    # ... DB 연결 코드 ...
    # AS를 사용하여 HTML에서 사용하는 변수명과 똑같이 맞춰줍니다.
    sql = """
    SELECT 
        prod_id, 
        prod_name, 
        prod_price, 
        prod_brand, 
        prod_img, 
        prod_category 
    FROM products
    """
    cursor.execute(sql)
    return cursor.fetchall() # dictionary=True 설정 필수