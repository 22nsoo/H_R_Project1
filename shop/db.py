import pymysql


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="123",
        database="shoppingmall3",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
