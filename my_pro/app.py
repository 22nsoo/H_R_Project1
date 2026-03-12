import os
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from db import get_connection
import json
import pymysql
import csv
from datetime import date, timedelta
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

# -----------------------------
# 파일 업로드 설정
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "products")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage):
    """
    업로드 파일을 저장하고 /static/... 경로를 반환한다.
    파일이 없으면 빈 문자열 반환.
    """
    if not file_storage or not file_storage.filename:
        return ""

    if not allowed_file(file_storage.filename):
        raise ValueError("이미지 파일은 jpg, jpeg, png, webp만 업로드할 수 있습니다.")

    original_name = secure_filename(file_storage.filename)
    ext = original_name.rsplit(".", 1)[1].lower()
    saved_name = f"{uuid.uuid4().hex}.{ext}"

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_name)
    file_storage.save(save_path)

    return f"/static/uploads/products/{saved_name}"


def parse_int(value, default=0):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def get_seller_or_none(cursor, seller_id: int):
    cursor.execute(
        """
        SELECT seller_id, seller_name, brand_name
        FROM sellers
        WHERE seller_id = %s
        """,
        (seller_id,)
    )
    return cursor.fetchone()

@app.route("/")
def home():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT seller_id, seller_name FROM sellers ORDER BY seller_id ASC")
    sellers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("home.html", sellers=sellers)


@app.route("/seller/dashboard/<int:seller_id>")
def seller_dashboard(seller_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT seller_id, seller_name FROM sellers WHERE seller_id = %s",
        (seller_id,)
    )
    seller = cursor.fetchone()

    if not seller:
        cursor.close()
        conn.close()
        return "판매자를 찾을 수 없습니다."
    
    #일매출
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS today_sales
        FROM orders
        WHERE seller_id = %s
        AND DATE(order_date) = CURDATE()
        AND order_status != '취소요청'
    """, (seller_id,))
    res = cursor.fetchone()
    today_sales = int(res["today_sales"] or 0)
    
    #월매출
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS month_sales
        FROM orders
        WHERE seller_id = %s
        AND YEAR(order_date) = YEAR(CURDATE())
        AND MONTH(order_date) = MONTH(CURDATE())
        AND order_status != '취소요청'
    """, (seller_id,))
    res = cursor.fetchone()
    month_sales = int(res["month_sales"] or 0)
    
    # 배송 미처리건
    cursor.execute("""
    SELECT COUNT(*) AS pending_orders
    FROM orders
    WHERE seller_id = %s
    AND order_status IN ('신규주문','배송준비중')
    """, (seller_id,))
    pending_orders = int(cursor.fetchone()["pending_orders"] or 0)

    # 문의 및 교환/환불
    cursor.execute("""
    SELECT COUNT(*) AS cs_count
    FROM customer_service
    WHERE seller_id = %s
    AND cs_status IN ('접수','처리중')
    """, (seller_id,))
    cs_count = int(cursor.fetchone()["cs_count"] or 0)
    
    cursor.execute("""
        SELECT
            p.product_name,
            p.category1,
            p.image_main1,
            SUM(oi.quantity) AS total_qty,
            SUM(oi.subtotal) AS total_sales
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.seller_id = %s
        GROUP BY p.product_id, p.product_name, p.category1, p.image_main1
        ORDER BY total_qty DESC, total_sales DESC
        LIMIT 5
    """, (seller_id,))
    top_products = cursor.fetchall()

    for item in top_products:
        item["total_qty"] = int(item["total_qty"] or 0)
        item["total_sales"] = int(item["total_sales"] or 0)

    cursor.execute("""
        SELECT product_id, product_name, stock, image_main1, category1
        FROM products
        WHERE seller_id = %s
        AND stock <= 5
        ORDER BY stock ASC, product_id ASC
        LIMIT 5
    """, (seller_id,))
    low_stock_products = cursor.fetchall()

    cursor.execute("""
        SELECT
            order_id,
            order_code,
            DATE(order_date) AS order_day,
            customer_name,
            order_status,
            total_amount
        FROM orders
        WHERE seller_id = %s
        ORDER BY order_date DESC, order_id DESC
        LIMIT 5
    """, (seller_id,))
    recent_orders = cursor.fetchall()

    for order in recent_orders:
        order["total_amount"] = int(order["total_amount"] or 0)

    # 일매출 그래프
    cursor.execute("""
    SELECT
        DATE(order_date) AS sales_date,
        COALESCE(SUM(total_amount), 0) AS daily_sales
    FROM orders
    WHERE seller_id = %s
    AND YEAR(order_date) = YEAR(CURDATE())
    AND MONTH(order_date) = MONTH(CURDATE())
    GROUP BY DATE(order_date)
    ORDER BY sales_date ASC
    """, (seller_id,))

    sales_map = {}
    for row in cursor.fetchall():
        sales_map[str(row["sales_date"])] = int(row["daily_sales"] or 0)

    today = date.today()

    labels = []
    values = []

    for d in range(1, today.day + 1):
        day = date(today.year, today.month, d)

        labels.append(day.strftime("%m/%d"))
        values.append(int(sales_map.get(str(day), 0)))

    # 월매출 그래프
    cursor.execute("""
    SELECT
        DATE_FORMAT(order_date,'%%Y-%%m') AS m,
        COALESCE(SUM(total_amount),0) AS sales
    FROM orders
    WHERE seller_id=%s
    GROUP BY DATE_FORMAT(order_date,'%%Y-%%m')
    ORDER BY m ASC
    """,(seller_id,))

    monthly_labels = []
    monthly_values = []

    for row in cursor.fetchall():
        monthly_labels.append(row["m"])
        monthly_values.append(int(row["sales"] or 0))

    cursor.close()
    conn.close()

    return render_template(
        "seller_dashboard.html",
        seller=seller,
        today_sales=today_sales,
        month_sales=month_sales,
        pending_orders=pending_orders,
        cs_count=cs_count,
        top_products=top_products,
        low_stock_products=low_stock_products,
        recent_orders=recent_orders,
        chart_labels=json.dumps(labels),
        chart_values=json.dumps(values),

        monthly_labels=json.dumps(monthly_labels),
        monthly_values=json.dumps(monthly_values)
    )

@app.route("/seller/products/<int:seller_id>")
def seller_products(seller_id):
    conn = get_connection()
    cursor = conn.cursor()

    seller = get_seller_or_none(cursor, seller_id)
    if not seller:
        cursor.close()
        conn.close()
        return "판매자를 찾을 수 없습니다."

    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "전체")
    sort = request.args.get("sort", "latest")

    page = request.args.get("page", 1, type=int)
    per_page = 10
    if page < 1:
        page = 1

    where_clauses = ["seller_id = %s"]
    params = [seller_id]

    if keyword:
        where_clauses.append("(product_name LIKE %s OR product_code LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if status and status != "전체":
        where_clauses.append("status = %s")
        params.append(status)

    where_sql = " AND ".join(where_clauses)

    order_sql = "ORDER BY product_id DESC"

    if sort == "product_code_asc":
        order_sql = "ORDER BY product_code ASC"
    elif sort == "product_code_desc":
        order_sql = "ORDER BY product_code DESC"
    elif sort == "brand_name_asc":
        order_sql = "ORDER BY brand_name ASC"
    elif sort == "brand_name_desc":
        order_sql = "ORDER BY brand_name DESC"
    elif sort == "product_name_asc":
        order_sql = "ORDER BY product_name ASC"
    elif sort == "product_name_desc":
        order_sql = "ORDER BY product_name DESC"
    elif sort == "category_asc":
        order_sql = "ORDER BY category1 ASC, category2 ASC"
    elif sort == "category_desc":
        order_sql = "ORDER BY category1 DESC, category2 DESC"
    elif sort == "price_asc":
        order_sql = "ORDER BY price ASC, product_id DESC"
    elif sort == "price_desc":
        order_sql = "ORDER BY price DESC, product_id DESC"
    elif sort == "stock_asc":
        order_sql = "ORDER BY stock ASC, product_id DESC"
    elif sort == "stock_desc":
        order_sql = "ORDER BY stock DESC, product_id DESC"
    elif sort == "status_asc":
        order_sql = """
            ORDER BY CASE status
                WHEN '판매중' THEN 1
                WHEN '품절' THEN 2
                WHEN '숨김' THEN 3
                ELSE 99
            END ASC, product_id DESC
        """
    elif sort == "status_desc":
        order_sql = """
            ORDER BY CASE status
                WHEN '판매중' THEN 1
                WHEN '품절' THEN 2
                WHEN '숨김' THEN 3
                ELSE 99
            END DESC, product_id DESC
        """

    count_sql = f"""
        SELECT COUNT(*) AS total_count
        FROM products
        WHERE {where_sql}
    """
    cursor.execute(count_sql, params)
    total_count = int(cursor.fetchone()["total_count"] or 0)

    total_pages = (total_count + per_page - 1) // per_page
    if total_pages == 0:
        total_pages = 1

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * per_page

    list_sql = f"""
        SELECT
            product_id,
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
            image_main1
        FROM products
        WHERE {where_sql}
        {order_sql}
        LIMIT %s OFFSET %s
    """
    cursor.execute(list_sql, (*params, per_page, offset))
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "seller_products.html",
        seller=seller,
        products=products,
        page=page,
        per_page=per_page,
        total_count=total_count,
        total_pages=total_pages,
        keyword=keyword,
        status=status,
        sort=sort,
    )

@app.route("/seller/product/add/<int:seller_id>", methods=["GET", "POST"])
def add_product(seller_id):
    conn = get_connection()
    cursor = conn.cursor()

    seller = get_seller_or_none(cursor, seller_id)
    if not seller:
        cursor.close()
        conn.close()
        return "판매자를 찾을 수 없습니다."

    if request.method == "POST":
        product_code = request.form.get("product_code", "").strip()
        product_name = request.form.get("product_name", "").strip()
        category1 = request.form.get("category1", "").strip()
        category2 = request.form.get("category2", "").strip()
        gender = request.form.get("gender", "공용").strip()
        price = parse_int(request.form.get("price", "0"))
        color = request.form.get("color", "").strip()
        size = request.form.get("size", "").strip()
        stock = parse_int(request.form.get("stock", "0"))
        status = request.form.get("status", "판매중").strip()
        description = request.form.get("description", "").strip()

        if not product_code:
            flash("상품코드를 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        if not product_name:
            flash("상품명을 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        if not category1 or not category2:
            flash("대분류와 중분류를 선택하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        if gender not in ["남성", "여성", "공용"]:
            flash("성별 값이 올바르지 않습니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        if status not in ["판매중", "품절", "숨김"]:
            flash("상품 상태 값이 올바르지 않습니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        try:
            image_main1 = save_uploaded_file(request.files.get("image_main1"))
            image_main2 = save_uploaded_file(request.files.get("image_main2"))
            image_main3 = save_uploaded_file(request.files.get("image_main3"))
            image_detail = save_uploaded_file(request.files.get("image_detail"))
        except ValueError as e:
            flash(str(e))
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        if not image_main1:
            flash("대표 이미지(image_main1)는 필수입니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM products
            WHERE product_code = %s
            """,
            (product_code,)
        )
        if int(cursor.fetchone()["cnt"] or 0) > 0:
            flash("이미 존재하는 상품코드입니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        cursor.execute(
            """
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
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                seller_id,
                product_code,
                seller["brand_name"],
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
                image_detail,
            )
        )
        conn.commit()

        cursor.close()
        conn.close()

        flash("상품이 등록되었습니다.")
        return redirect(url_for("seller_products", seller_id=seller_id))

    cursor.close()
    conn.close()
    return render_template("product_form.html", seller=seller, mode="add", product=None)

@app.route("/seller/product/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            product_id,
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
        FROM products
        WHERE product_id = %s
        """,
        (product_id,)
    )
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "상품을 찾을 수 없습니다."

    seller = get_seller_or_none(cursor, product["seller_id"])
    if not seller:
        cursor.close()
        conn.close()
        return "판매자를 찾을 수 없습니다."

    if request.method == "POST":
        product_code = request.form.get("product_code", "").strip()
        product_name = request.form.get("product_name", "").strip()
        category1 = request.form.get("category1", "").strip()
        category2 = request.form.get("category2", "").strip()
        gender = request.form.get("gender", "공용").strip()
        price = parse_int(request.form.get("price", "0"))
        color = request.form.get("color", "").strip()
        size = request.form.get("size", "").strip()
        stock = parse_int(request.form.get("stock", "0"))
        status = request.form.get("status", "판매중").strip()
        description = request.form.get("description", "").strip()

        if not product_code:
            flash("상품코드를 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        if not product_name:
            flash("상품명을 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        if not category1 or not category2:
            flash("대분류와 중분류를 선택하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        if gender not in ["남성", "여성", "공용"]:
            flash("성별 값이 올바르지 않습니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        if status not in ["판매중", "품절", "숨김"]:
            flash("상품 상태 값이 올바르지 않습니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM products
            WHERE product_code = %s
              AND product_id <> %s
            """,
            (product_code, product_id)
        )
        if int(cursor.fetchone()["cnt"] or 0) > 0:
            flash("이미 존재하는 상품코드입니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        try:
            new_image_main1 = save_uploaded_file(request.files.get("image_main1"))
            new_image_main2 = save_uploaded_file(request.files.get("image_main2"))
            new_image_main3 = save_uploaded_file(request.files.get("image_main3"))
            new_image_detail = save_uploaded_file(request.files.get("image_detail"))
        except ValueError as e:
            flash(str(e))
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        image_main1 = new_image_main1 if new_image_main1 else product["image_main1"]
        image_main2 = new_image_main2 if new_image_main2 else product["image_main2"]
        image_main3 = new_image_main3 if new_image_main3 else product["image_main3"]
        image_detail = new_image_detail if new_image_detail else product["image_detail"]

        if not image_main1:
            flash("대표 이미지(image_main1)는 필수입니다.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        cursor.execute(
            """
            UPDATE products
            SET
                product_code = %s,
                brand_name = %s,
                product_name = %s,
                category1 = %s,
                category2 = %s,
                gender = %s,
                price = %s,
                color = %s,
                size = %s,
                stock = %s,
                status = %s,
                description = %s,
                image_main1 = %s,
                image_main2 = %s,
                image_main3 = %s,
                image_detail = %s
            WHERE product_id = %s
            """,
            (
                product_code,
                seller["brand_name"],
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
                image_detail,
                product_id,
            )
        )
        conn.commit()

        seller_id = product["seller_id"]

        cursor.close()
        conn.close()

        flash("상품이 수정되었습니다.")
        return redirect(url_for("seller_products", seller_id=seller_id))

    cursor.close()
    conn.close()
    return render_template("product_form.html", seller=seller, mode="edit", product=product)

@app.route("/seller/product/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT seller_id FROM products WHERE product_id = %s",
        (product_id,)
    )
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "상품을 찾을 수 없습니다."

    seller_id = product["seller_id"]

    cursor.execute(
        "DELETE FROM products WHERE product_id = %s",
        (product_id,)
    )
    conn.commit()

    cursor.close()
    conn.close()

    flash("상품이 삭제되었습니다.")
    return redirect(url_for("seller_products", seller_id=seller_id))

@app.route("/seller/products/delete-selected/<int:seller_id>", methods=["POST"])
def delete_selected_products(seller_id):
    product_ids = request.form.getlist("product_ids")

    if not product_ids:
        flash("선택된 상품이 없습니다.")
        return redirect(url_for("seller_products", seller_id=seller_id))

    filtered_ids = []
    for pid in product_ids:
        try:
            filtered_ids.append(int(pid))
        except ValueError:
            continue

    if not filtered_ids:
        flash("삭제할 상품 정보가 올바르지 않습니다.")
        return redirect(url_for("seller_products", seller_id=seller_id))

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join(["%s"] * len(filtered_ids))
    sql = f"""
        DELETE FROM products
        WHERE seller_id = %s
        AND product_id IN ({placeholders})
    """
    cursor.execute(sql, (seller_id, *filtered_ids))
    conn.commit()

    cursor.close()
    conn.close()

    flash("선택한 상품이 삭제되었습니다.")
    return redirect(url_for("seller_products", seller_id=seller_id))

@app.route("/seller/products/delete-all/<int:seller_id>", methods=["POST"])
def delete_all_products(seller_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM products WHERE seller_id = %s",
        (seller_id,)
    )
    conn.commit()

    cursor.close()
    conn.close()

    flash("전체 상품이 삭제되었습니다.")
    return redirect(url_for("seller_products", seller_id=seller_id))

@app.route("/seller/product/stock/<int:product_id>", methods=["POST"])
def update_product_stock(product_id):
    new_stock = parse_int(request.form.get("stock", "0"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT seller_id FROM products WHERE product_id = %s",
        (product_id,)
    )
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "상품을 찾을 수 없습니다."

    status = "판매중" if new_stock > 0 else "품절"

    cursor.execute(
        """
        UPDATE products
        SET stock = %s, status = %s
        WHERE product_id = %s
        """,
        (new_stock, status, product_id)
    )
    conn.commit()

    seller_id = product["seller_id"]

    cursor.close()
    conn.close()

    flash("재고가 수정되었습니다.")
    return redirect(url_for("seller_dashboard", seller_id=seller_id))

@app.route("/seller/orders/<int:seller_id>")
def seller_orders(seller_id):
    keyword = request.args.get("keyword")
    status = request.args.get("status")
    sort = request.args.get("sort")
    type_filter = request.args.get("type")

    conn = get_connection()
    cursor = conn.cursor()
    
    # 판매자 조회
    cursor.execute(
        "SELECT seller_id, seller_name FROM sellers WHERE seller_id = %s",
        (seller_id,)
    )
    seller = cursor.fetchone()

    if not seller:
        cursor.close()
        conn.close()
        return "판매자를 찾을 수 없습니다."

    query = """
    SELECT order_id, order_code, customer_name, customer_email,
        customer_phone, address,
        order_date, total_amount, order_status
    FROM orders
    WHERE seller_id = %s
    """

    params = [seller_id]
    # 배송 미처리 필터
    if type_filter == "pending":
        query += " AND order_status IN ('신규주문','배송준비중')"

    # 주문번호 검색
    if keyword:
        query += " AND order_code LIKE %s"
        params.append(f"%{keyword}%")

    # 상태 필터
    if status and status != "전체":
        query += " AND order_status = %s"
        params.append(status)

    # 정렬
    if sort == "price_desc":
        query += " ORDER BY total_amount DESC"
    elif sort == "price_asc":
        query += " ORDER BY total_amount ASC"
    else:
        query += " ORDER BY order_date DESC"

    cursor.execute(query, params)
    orders = cursor.fetchall()

    for order in orders:
        order["total_amount"] = int(order["total_amount"] or 0)

    cursor.close()
    conn.close()

    return render_template(
        "seller_orders.html",
        seller=seller,
        orders=orders
    )

@app.route("/seller/sales/<int:seller_id>")
def seller_sales(seller_id):

    conn = get_connection()
    cursor = conn.cursor()
    
    # 연도 파라미터 받기
    year = request.args.get("year", type=int)
    if not year:
        year = date.today().year

    # 기간 파라미터 추가 
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date:
        start_date = date.today().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    # 판매자 정보
    cursor.execute(
        "SELECT seller_id, seller_name FROM sellers WHERE seller_id=%s",
        (seller_id,)
    )
    seller = cursor.fetchone()

    if not seller:
        cursor.close()
        conn.close()
        return "판매자를 찾을 수 없습니다."

    # -------------------------
    # 일 매출
    # -------------------------
    cursor.execute("""
        SELECT DATE(order_date) AS d,
        SUM(total_amount) AS sales
        FROM orders
        WHERE seller_id=%s
        AND order_status != '취소요청'
        AND DATE(order_date) BETWEEN %s AND %s
        GROUP BY DATE(order_date) 
        ORDER BY d ASC
        LIMIT 30
    """, (seller_id,start_date, end_date))
    daily_sales = cursor.fetchall()

    daily_labels = []
    daily_values = []

    for row in daily_sales:
        daily_labels.append(str(row["d"]))
        daily_values.append(int(row["sales"] or 0))
    
    # -------------------------
    # 월 매출
    # -------------------------
    cursor.execute("""
        SELECT DATE_FORMAT(order_date,'%%Y-%%m') AS m,
        COALESCE(SUM(total_amount),0) AS sales
        FROM orders
        WHERE seller_id=%s
        AND order_status != '취소요청'
        AND YEAR(order_date)=%s
        GROUP BY DATE_FORMAT(order_date,'%%Y-%%m')
        ORDER BY m ASC
    """, (seller_id,year))
    monthly_sales = cursor.fetchall()
    
    monthly_labels = []
    monthly_values = []

    for row in monthly_sales:
        monthly_labels.append(row["m"])
        monthly_values.append(int(row["sales"] or 0))

    # -------------------------
    # 연 매출
    # -------------------------
    cursor.execute("""
    SELECT YEAR(order_date) AS y,
    SUM(total_amount) AS sales
    FROM orders
    WHERE seller_id=%s
    GROUP BY YEAR(order_date)
    ORDER BY y ASC
                   
    """,(seller_id,))

    yearly_sales = cursor.fetchall()

    yearly_labels = []
    yearly_values = []

    for row in yearly_sales:
        yearly_labels.append(str(row["y"]))
        yearly_values.append(int(row["sales"] or 0))

    # -------------------------
    # 연도 목록 가져오기
    # -------------------------
    cursor.execute("""
    SELECT DISTINCT YEAR(order_date) AS y
    FROM orders
    WHERE seller_id=%s
    ORDER BY y DESC
    """,(seller_id,))

    year_list = [row["y"] for row in cursor.fetchall()]

    # ------------------------------------------
    #  총 매출 / 총 주문 / 평균 주문금액 카드 추가
    # ------------------------------------------
    cursor.execute("""
    SELECT
        COALESCE(SUM(total_amount),0) AS total_sales,
        COUNT(order_id) AS total_orders
    FROM orders
    WHERE seller_id=%s 
    """,(seller_id,))

    summary = cursor.fetchone()

    total_sales = int(summary["total_sales"] or 0)
    total_orders = int(summary["total_orders"] or 0)

    avg_order = int(total_sales / total_orders) if total_orders > 0 else 0

    cursor.close()
    conn.close()

    return render_template(
        "seller_sales.html",
        seller=seller,
        year=year,
        year_list=year_list,

        start_date=start_date,
        end_date=end_date,

        total_sales=total_sales,
        total_orders=total_orders,
        avg_order=avg_order,

        daily_sales=daily_sales,
        monthly_sales=monthly_sales,
        yearly_sales=yearly_sales,

        daily_labels=json.dumps(daily_labels),
        daily_values=json.dumps(daily_values),

        monthly_labels=json.dumps(monthly_labels),
        monthly_values=json.dumps(monthly_values),

        yearly_labels=json.dumps(yearly_labels),
        yearly_values=json.dumps(yearly_values)
    )
    

# 일 매출 다운로드 CSV 추가
@app.route("/seller/sales/export/<int:seller_id>")
def export_sales_csv(seller_id):

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DATE(order_date) AS date,
            COUNT(order_id) AS order_count,
            SUM(total_amount) AS sales
        FROM orders
        WHERE seller_id=%s 
        AND order_status != '취소요청'
        AND DATE(order_date) BETWEEN %s AND %s
        GROUP BY DATE(order_date)
        ORDER BY date DESC
    """, (seller_id, start_date, end_date))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    def generate():
        yield '\ufeff'   # UTF-8 BOM (엑셀 한글 깨짐 방지)
        yield "날짜,주문수,매출\n"
        for r in rows:
            yield f"{r['date']},{r['order_count']},{r['sales']}\n"

    filename = f"sales_{start_date}_{end_date}.csv"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# 월 매출 CSV 다운로드
@app.route("/seller/sales/export_month/<int:seller_id>")
def export_month_sales_csv(seller_id):

    year = request.args.get("year")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DATE_FORMAT(order_date,'%%Y-%%m') AS month,
        SUM(total_amount) AS sales
        FROM orders
        WHERE seller_id=%s
        AND order_status != '취소요청'
        AND YEAR(order_date)=%s
        GROUP BY DATE_FORMAT(order_date,'%%Y-%%m')
        ORDER BY month DESC
    """,(seller_id,year))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    def generate():
        yield '\ufeff'
        yield "월,매출\n"

        for r in rows:
            sales = r["sales"] or 0
            yield f"{r['month']},{sales}\n"

    filename = f"monthly_sales_{year}.csv"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# 연 매출 CSV 다운로드
@app.route("/seller/sales/export_year/<int:seller_id>")
def export_year_sales_csv(seller_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT YEAR(order_date) AS year,
        SUM(total_amount) AS sales
        FROM orders
        WHERE seller_id=%s
        AND order_status != '취소요청'
        GROUP BY YEAR(order_date)
        ORDER BY year DESC
    """,(seller_id,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    def generate():
        yield '\ufeff'
        yield "연도,매출\n"

        for r in rows:
            sales = r["sales"] or 0
            yield f"{r['year']},{sales}\n"

    filename = "yearly_sales.csv"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# 판매자 CS (문의 + 교환/환불 관리)
@app.route("/seller/cs/<int:seller_id>")
def seller_cs(seller_id):

    page_q = request.args.get("page_q", 1, type=int)
    page_r = request.args.get("page_r", 1, type=int)

    per_page = 5

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 판매자 정보
    cursor.execute("""
        SELECT seller_id, seller_name
        FROM sellers
        WHERE seller_id=%s
    """, (seller_id,))
    seller = cursor.fetchone()

    # 상품 문의 개수
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM customer_service
        WHERE seller_id=%s
        AND cs_type='상품문의'
    """, (seller_id,))
    total_q = cursor.fetchone()["cnt"]

    # 상품 문의 데이터
    cursor.execute("""
        SELECT
            cs.cs_id,
            cs.customer_name,
            cs.cs_title,
            cs.cs_content,
            cs.cs_reply,
            cs.cs_status,
            cs.created_at,
            p.product_name
        FROM customer_service cs
        JOIN products p ON cs.product_id = p.product_id
        WHERE cs.seller_id=%s
        AND cs.cs_type='상품문의'
        ORDER BY
            CASE cs.cs_status
                WHEN '접수' THEN 0
                WHEN '처리완료' THEN 1
            END,
            cs.created_at DESC
        LIMIT %s OFFSET %s
    """, (seller_id, per_page, (page_q-1)*per_page))

    questions = cursor.fetchall()

    # =====================
    # 교환 / 반품 개수
    # =====================
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM customer_service
        WHERE seller_id=%s
        AND cs_type IN ('교환요청','반품요청')
    """, (seller_id,))
    total_r = cursor.fetchone()["cnt"]

    # 교환 / 반품 데이터
    cursor.execute("""
        SELECT
            cs.cs_id,
            cs.customer_name,
            cs.cs_type,
            cs.cs_content,
            cs.cs_status,
            o.order_code,
            p.product_name
        FROM customer_service cs
        JOIN orders o ON cs.order_id = o.order_id
        JOIN products p ON cs.product_id = p.product_id
        WHERE cs.seller_id=%s
        AND cs.cs_type IN ('교환요청','반품요청')
        ORDER BY
            CASE cs.cs_status
                WHEN '접수' THEN 0
                WHEN '처리중' THEN 1
                WHEN '처리완료' THEN 2
            END,
            cs.created_at DESC
        LIMIT %s OFFSET %s
    """, (seller_id, per_page, (page_r-1)*per_page))

    returns = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages_q = (total_q + per_page - 1) // per_page
    total_pages_r = (total_r + per_page - 1) // per_page

    return render_template(
        "seller_cs.html",
        seller=seller,
        questions=questions,
        returns=returns,
        seller_id=seller_id,
        page_q=page_q,
        page_r=page_r,
        total_pages_q=total_pages_q,
        total_pages_r=total_pages_r,
    )

# 답변 등록 기능
@app.route("/seller/cs/reply/<int:cs_id>", methods=["POST"])
def reply_cs(cs_id):

    reply = request.form.get("reply","").strip()

    if not reply:
        return redirect(request.referrer)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE customer_service
        SET cs_reply=%s,
            cs_status='처리완료'
        WHERE cs_id=%s
    """,(reply,cs_id))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(request.referrer)

@app.route("/seller/cs/status/<int:cs_id>", methods=["POST"])
def update_cs_status(cs_id):

    new_status = request.form.get("cs_status")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE customer_service
        SET cs_status=%s
        WHERE cs_id=%s
    """,(new_status,cs_id))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(request.referrer)
    
@app.route("/seller/order/status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    new_status = request.form.get("order_status", "").strip()

    allowed_status = ["신규주문", "배송준비중", "배송중", "배송완료", "반품요청", "교환요청"]
    if new_status not in allowed_status:
        return "잘못된 주문 상태입니다."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT seller_id FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        conn.close()
        return "주문을 찾을 수 없습니다."

    cursor.execute("""
        UPDATE orders
        SET order_status = %s
        WHERE order_id = %s
    """, (new_status, order_id))
    conn.commit()

    seller_id = order["seller_id"]

    cursor.close()
    conn.close()

    # flash("주문 상태가 변경되었습니다.")
    return redirect(url_for("seller_orders", seller_id=seller_id))


# 삭제 
@app.route("/seller/cs/delete", methods=["POST"])
def delete_cs():

    ids = request.form.getlist("delete_ids")

    if not ids:
        return redirect(request.referrer)

    conn = get_connection()
    cursor = conn.cursor()

    for cs_id in ids:
        cursor.execute(
            "DELETE FROM customer_service WHERE cs_id=%s",
            (cs_id,)
        )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(request.referrer)
if __name__ == "__main__":
    app.run(debug=True)