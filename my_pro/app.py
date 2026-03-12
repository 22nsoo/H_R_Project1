from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_connection
import json
import pymysql
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = "secret123"


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
    AND cs_status != '완료'
    """, (seller_id,))
    cs_count = int(cursor.fetchone()["cs_count"] or 0)
    
    # 총 주문 수 
    # cursor.execute("""
    #     SELECT COUNT(*) AS total_orders
    #     FROM orders
    #     WHERE seller_id = %s
    # """, (seller_id,))
    # total_orders = int(cursor.fetchone()["total_orders"] or 0)
    
    # 판매 상품 
    # cursor.execute("""
    #     SELECT COUNT(*) AS active_products
    #     FROM products
    #     WHERE seller_id = %s
    #     AND status = '판매중'
    # """, (seller_id,))
    # active_products = int(cursor.fetchone()["active_products"] or 0)

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

    cursor.execute("""
        SELECT
            DATE(order_date) AS sales_date,
            COALESCE(SUM(total_amount), 0) AS daily_sales
        FROM orders
        WHERE seller_id = %s
        AND order_status != '취소'
        AND order_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY DATE(order_date)
        ORDER BY sales_date ASC
    """, (seller_id,))

    sales_map = {}
    for row in cursor.fetchall():
        sales_map[str(row["sales_date"])] = int(row["daily_sales"] or 0)

    labels = []
    values = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        labels.append(d.strftime("%m/%d"))
        values.append(int(sales_map.get(str(d), 0)))

    cursor.close()
    conn.close()

    return render_template(
        "seller_dashboard.html",
        seller=seller,
        today_sales=today_sales,
        month_sales=month_sales,
        pending_orders=pending_orders,
        cs_count=cs_count,
        # total_orders=total_orders,
        # active_products=active_products,
        top_products=top_products,
        low_stock_products=low_stock_products,
        recent_orders=recent_orders,
        chart_labels=json.dumps(labels, ensure_ascii=False),
        chart_values=json.dumps(values, ensure_ascii=False),
    )


@app.route("/seller/products/<int:seller_id>")
def seller_products(seller_id):
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

    cursor.execute("""
        SELECT product_id, seller_id, product_name, category1, price, stock, status, image_main1
        FROM products
        WHERE seller_id = %s
        ORDER BY product_id DESC
    """, (seller_id,))
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("seller_products.html", seller=seller, products=products)


@app.route("/seller/product/add/<int:seller_id>", methods=["GET", "POST"])
def add_product(seller_id):
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

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        category = request.form.get("category1", "").strip()
        price = request.form.get("price", "0").strip()
        stock = request.form.get("stock", "0").strip()
        status = request.form.get("status", "판매중").strip()
        image_url = request.form.get("image_main1", "").strip()

        if not product_name:
            flash("상품명을 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        try:
            price = int(price)
            stock = int(stock)
        except ValueError:
            flash("가격과 재고는 숫자로 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="add", product=None)

        cursor.execute("""
            INSERT INTO products (seller_id, product_name, category1, price, stock, status, image_main1)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (seller_id, product_name, category, price, stock, status, image_url))
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

    cursor.execute("""
        SELECT product_id, seller_id, product_name, category1, price, stock, status, image_main1
        FROM products
        WHERE product_id = %s
    """, (product_id,))
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "상품을 찾을 수 없습니다."

    cursor.execute(
        "SELECT seller_id, seller_name FROM sellers WHERE seller_id = %s",
        (product["seller_id"],)
    )
    seller = cursor.fetchone()

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        category = request.form.get("category1", "").strip()
        price = request.form.get("price", "0").strip()
        stock = request.form.get("stock", "0").strip()
        status = request.form.get("status", "판매중").strip()
        image_url = request.form.get("image_main1", "").strip()

        if not product_name:
            flash("상품명을 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        try:
            price = int(price)
            stock = int(stock)
        except ValueError:
            flash("가격과 재고는 숫자로 입력하세요.")
            cursor.close()
            conn.close()
            return render_template("product_form.html", seller=seller, mode="edit", product=product)

        cursor.execute("""
            UPDATE products
            SET product_name = %s,
                category1 = %s,
                price = %s,
                stock = %s,
                status = %s,
                image_main1 = %s
            WHERE product_id = %s
        """, (product_name, category, price, stock, status, image_url, product_id))
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

    cursor.execute("SELECT seller_id FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "상품을 찾을 수 없습니다."

    seller_id = product["seller_id"]

    cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("상품이 삭제되었습니다.")
    return redirect(url_for("seller_products", seller_id=seller_id))


@app.route("/seller/product/stock/<int:product_id>", methods=["POST"])
def update_product_stock(product_id):
    new_stock = request.form.get("stock", "0").strip()

    try:
        new_stock = int(new_stock)
    except ValueError:
        return "재고는 숫자로 입력해야 합니다."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT seller_id FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "상품을 찾을 수 없습니다."

    status = "판매중" if new_stock > 0 else "품절"

    cursor.execute("""
        UPDATE products
        SET stock = %s, status = %s
        WHERE product_id = %s
    """, (new_stock, status, product_id))
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


# 판매자 CS (문의 + 교환/환불 관리)
@app.route("/seller/cs/<int:seller_id>")
def seller_cs(seller_id):

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 상품 문의
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
        ORDER BY cs.created_at DESC
    """, (seller_id,))
    questions = cursor.fetchall()

    # 교환 / 반품 요청
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
        ORDER BY cs.created_at DESC
    """, (seller_id,))
    returns = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "seller_cs.html",
        questions=questions,
        returns=returns,
        seller_id=seller_id
    )

# 답변 등록 기능
@app.route("/seller/cs/reply/<int:cs_id>", methods=["POST"])
def reply_cs(cs_id):

    reply = request.form["reply"]

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


if __name__ == "__main__":
    app.run(debug=True, port=5001)