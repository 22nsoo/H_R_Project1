import pymysql

# 기존에 있던 get_connection 함수 (사용자 정보용)
import pymysql

def get_connection():
    return pymysql.connect(
        host="192.168.0.247",
        user="shopuser",
        password="shop1234!",
        database="shoppingmall3",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

