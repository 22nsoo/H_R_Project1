import pymysql


def get_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="123",
        database="shoppingmall",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )