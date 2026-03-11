import pymysql


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="123",
        database="shoppingmall",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )