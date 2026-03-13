from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from db import get_connection
from jinja2 import TemplateNotFound
from werkzeug.utils import secure_filename
import time
import os
import math
import json
import csv
import io
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "musinsa_secret_key"

UPLOAD_DIR = os.path.join("static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# 공통 유틸
# =========================
def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


def _dict_or_empty(row):
    return row if isinstance(row, dict) and row else {}


def _today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _days_ago_str(days):
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def _json_dump(value):
    return json.dumps(value, ensure_ascii=False)


def _csv_response(filename, headers, rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _merge_product_row(row):
    row = _dict_or_empty(row)
    return {
        "id": row.get("product_id"),
        "product_id": row.get("product_id"),
        "name": row.get("product_name"),
        "product_name": row.get("product_name"),
        "price": row.get("price") or 0,
        "brand": row.get("brand_name") or "",
        "brand_name": row.get("brand_name") or "",
        "desc": row.get("description") or "",
        "description": row.get("description") or "",
        "category": row.get("category1") or "",
        "category1": row.get("category1") or "",
        "category2": row.get("category2") or "",
        "img": row.get("image_main1") or "",
        "image_main1": row.get("image_main1") or "",
        "image_main2": row.get("image_main2") or "",
        "image_main3": row.get("image_main3") or "",
        "image_detail": row.get("image_detail") or "",
        "size_options": row.get("size") or "",
        "size": row.get("size") or "",
        "stock": row.get("stock") or 0,
        "status": row.get("status") or "",
        "product_code": row.get("product_code") or "",
        "seller_id": row.get("seller_id"),
        "color": row.get("color") or "",
        "gender": row.get("gender") or "",
    }


def get_all_products():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM products
                WHERE status <> '숨김'
                ORDER BY product_id ASC
            """)
            rows = cursor.fetchall()
        return [_merge_product_row(row) for row in rows]
    finally:
        conn.close()


def get_product_by_id(product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM products
                WHERE product_id = %s
            """, (product_id,))
            row = cursor.fetchone()

            if not row:
                return None

        return _merge_product_row(row)
    finally:
        conn.close()


def has_purchased_product(user_id, product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT 1
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.user_id = %s
                  AND oi.product_id = %s
                LIMIT 1
            """
            cur.execute(sql, (user_id, product_id))
            return cur.fetchone() is not None
    finally:
        conn.close()


def has_existing_review(user_id, product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT 1
                FROM reviews
                WHERE user_id = %s
                  AND product_id = %s
                LIMIT 1
            """
            cur.execute(sql, (user_id, product_id))
            return cur.fetchone() is not None
    finally:
        conn.close()


def match_products_from_image_results(image_results, items):
    item_map = {item["id"]: item for item in items if item.get("id") is not None}
    matched = []

    for result in image_results:
        product_id = result.get("product_id")
        if product_id in item_map:
            item = item_map[product_id]
            if item not in matched:
                matched.append(item)

    return matched


def save_uploaded_file(file_obj):
    if not file_obj or not getattr(file_obj, "filename", ""):
        return ""
    filename = secure_filename(file_obj.filename)
    if not filename:
        return ""
    save_path = os.path.join(UPLOAD_DIR, filename)
    file_obj.save(save_path)
    return "/" + save_path.replace("\\", "/")


def render_optional_template(template_name, **context):
    try:
        return render_template(template_name, **context)
    except TemplateNotFound:
        title = context.get("title", template_name)
        body = f"""
        <html lang="ko">
        <head><meta charset="utf-8"><title>{title}</title></head>
        <body style="font-family:Pretendard,sans-serif; padding:40px;">
            <h1>{title}</h1>
            <p>현재 <strong>{template_name}</strong> 템플릿 파일이 프로젝트에 없습니다.</p>
            <p>백엔드 라우트는 연결되어 있으니, 템플릿만 추가하면 됩니다.</p>
            <p><a href="/seller/dashboard">판매자 대시보드로 돌아가기</a></p>
        </body>
        </html>
        """
        return body


# =========================
# 판매자 관련 helper
# =========================
def get_first_available_seller():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT seller_id, seller_name, brand_name
                    FROM sellers
                    ORDER BY seller_id ASC
                    LIMIT 1
                """)
                seller = cur.fetchone()
                if seller:
                    return seller
            except Exception:
                pass

            try:
                cur.execute("""
                    SELECT seller_id
                    FROM products
                    WHERE seller_id IS NOT NULL
                    GROUP BY seller_id
                    ORDER BY seller_id ASC
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    sid = row.get("seller_id")
                    return {
                        "seller_id": sid,
                        "seller_name": f"판매자 {sid}",
                        "brand_name": ""
                    }
            except Exception:
                pass

        return {"seller_id": 1, "seller_name": "기본 판매자", "brand_name": ""}
    finally:
        conn.close()


def get_sellers_for_home():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT seller_id, seller_name, brand_name
                    FROM sellers
                    ORDER BY seller_id ASC
                """)
                sellers = cur.fetchall()
                if sellers:
                    return sellers
            except Exception:
                pass

            try:
                cur.execute("""
                    SELECT seller_id
                    FROM products
                    WHERE seller_id IS NOT NULL
                    GROUP BY seller_id
                    ORDER BY seller_id ASC
                """)
                rows = cur.fetchall()
                return [
                    {
                        "seller_id": r.get("seller_id"),
                        "seller_name": f"판매자 {r.get('seller_id')}",
                        "brand_name": ""
                    }
                    for r in rows
                ]
            except Exception:
                return []
    finally:
        conn.close()


def get_current_seller():
    seller_id = session.get("seller_id")
    if not seller_id:
        seller = get_first_available_seller()
        session["seller_id"] = seller["seller_id"]
        session["role"] = "seller"
        return seller

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT seller_id, seller_name, brand_name
                    FROM sellers
                    WHERE seller_id = %s
                """, (seller_id,))
                seller = cur.fetchone()
                if seller:
                    return seller
            except Exception:
                pass

        return {
            "seller_id": seller_id,
            "seller_name": f"판매자 {seller_id}",
            "brand_name": ""
        }
    finally:
        conn.close()


def require_seller():
    if session.get("role") not in ["seller", "admin"]:
        flash("판매자/관리자 로그인이 필요합니다.")
        return False
    return True


def ensure_seller_session():
    if not session.get("seller_id"):
        seller = get_first_available_seller()
        session["seller_id"] = seller["seller_id"]
        session["role"] = "seller"


def get_seller_products(seller_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM products
                WHERE seller_id = %s
                ORDER BY product_id DESC
            """, (seller_id,))
            return [_merge_product_row(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_dashboard_data(seller_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT COALESCE(SUM(total_amount), 0) AS total
                    FROM orders
                    WHERE seller_id = %s
                      AND DATE(order_date) = CURDATE()
                """, (seller_id,))
                today_sales = _safe_int(cur.fetchone().get("total"))
            except Exception:
                today_sales = 0

            try:
                cur.execute("""
                    SELECT COALESCE(SUM(total_amount), 0) AS total
                    FROM orders
                    WHERE seller_id = %s
                      AND YEAR(order_date) = YEAR(CURDATE())
                      AND MONTH(order_date) = MONTH(CURDATE())
                """, (seller_id,))
                month_sales = _safe_int(cur.fetchone().get("total"))
            except Exception:
                month_sales = 0

            try:
                cur.execute("""
                    SELECT COUNT(*) AS cnt
                    FROM orders
                    WHERE seller_id = %s
                      AND order_status IN ('신규주문', '배송준비중')
                """, (seller_id,))
                pending_orders = _safe_int(cur.fetchone().get("cnt"))
            except Exception:
                pending_orders = 0

            try:
                cur.execute("""
                    SELECT COUNT(*) AS cnt
                    FROM customer_service
                    WHERE seller_id = %s
                """, (seller_id,))
                cs_count = _safe_int(cur.fetchone().get("cnt"))
            except Exception:
                cs_count = 0

            try:
                cur.execute("""
                    SELECT
                        p.product_id,
                        p.product_name,
                        p.image_main1,
                        p.category1,
                        COALESCE(SUM(oi.quantity), 0) AS total_qty,
                        COALESCE(SUM(oi.subtotal), 0) AS total_sales
                    FROM products p
                    LEFT JOIN order_items oi ON p.product_id = oi.product_id
                    WHERE p.seller_id = %s
                    GROUP BY p.product_id, p.product_name, p.image_main1, p.category1
                    ORDER BY total_sales DESC, total_qty DESC
                    LIMIT 5
                """, (seller_id,))
                top_products = cur.fetchall()
            except Exception:
                top_products = []

            try:
                cur.execute("""
                    SELECT product_id, product_name, image_main1, stock
                    FROM products
                    WHERE seller_id = %s
                      AND stock <= 5
                    ORDER BY stock ASC, product_id DESC
                    LIMIT 5
                """, (seller_id,))
                low_stock_products = cur.fetchall()
            except Exception:
                low_stock_products = []

            try:
                cur.execute("""
                    SELECT order_id, order_code, customer_name, total_amount, order_status
                    FROM orders
                    WHERE seller_id = %s
                    ORDER BY order_date DESC
                    LIMIT 5
                """, (seller_id,))
                recent_orders = cur.fetchall()
            except Exception:
                recent_orders = []

            chart_labels = []
            chart_values = []
            try:
                cur.execute("""
                    SELECT DATE(order_date) AS d, COALESCE(SUM(total_amount), 0) AS total
                    FROM orders
                    WHERE seller_id = %s
                      AND order_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
                    GROUP BY DATE(order_date)
                    ORDER BY d ASC
                """, (seller_id,))
                rows = cur.fetchall()
                day_map = {str(r.get("d")): _safe_int(r.get("total")) for r in rows}

                for i in range(6, -1, -1):
                    dt = datetime.now() - timedelta(days=i)
                    key = dt.strftime("%Y-%m-%d")
                    chart_labels.append(dt.strftime("%m-%d"))
                    chart_values.append(day_map.get(key, 0))
            except Exception:
                chart_labels = ["월", "화", "수", "목", "금", "토", "일"]
                chart_values = [0, 0, 0, 0, 0, 0, 0]

            monthly_labels = []
            monthly_values = []
            try:
                cur.execute("""
                    SELECT DATE_FORMAT(order_date, '%%Y-%%m') AS ym, COALESCE(SUM(total_amount), 0) AS total
                    FROM orders
                    WHERE seller_id = %s
                      AND order_date >= DATE_SUB(CURDATE(), INTERVAL 5 MONTH)
                    GROUP BY DATE_FORMAT(order_date, '%%Y-%%m')
                    ORDER BY ym ASC
                """, (seller_id,))
                rows = cur.fetchall()
                month_map = {r.get("ym"): _safe_int(r.get("total")) for r in rows}

                for i in range(5, -1, -1):
                    dt = datetime.now().replace(day=1) - timedelta(days=30 * i)
                    key = dt.strftime("%Y-%m")
                    monthly_labels.append(key)
                    monthly_values.append(month_map.get(key, 0))
            except Exception:
                monthly_labels = []
                monthly_values = []

            return {
                "today_sales": today_sales,
                "month_sales": month_sales,
                "pending_orders": pending_orders,
                "cs_count": cs_count,
                "top_products": top_products,
                "low_stock_products": low_stock_products,
                "recent_orders": recent_orders,
                "chart_labels": _json_dump(chart_labels),
                "chart_values": _json_dump(chart_values),
                "monthly_labels": _json_dump(monthly_labels),
                "monthly_values": _json_dump(monthly_values),
            }
    finally:
        conn.close()


# =========================
# 일반 사용자 라우트
# =========================
@app.route("/")
def home():
    return redirect(url_for("main_page"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    user_id = request.form.get("user_id", "").strip()
    user_pw = request.form.get("user_pw", "").strip()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username=%s", (user_id,))
            user = cursor.fetchone()

            if user and user.get("password") == user_pw:
                session["user_id"] = user.get("user_id")
                session["user_name"] = user.get("username")
                return redirect(url_for("main_page"))
    finally:
        conn.close()

    flash("아이디 또는 비밀번호가 틀렸습니다.")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main_page"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    admin_id = request.form.get("admin_id", "").strip()
    admin_pw = request.form.get("admin_pw", "").strip()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    a.account_id,
                    a.login_id,
                    a.password,
                    a.role,
                    a.is_active,
                    s.seller_id,
                    s.seller_name,
                    s.brand_name
                FROM accounts a
                LEFT JOIN sellers s
                    ON a.account_id = s.account_id
                WHERE a.login_id = %s
                LIMIT 1
            """, (admin_id,))
            account = cur.fetchone()

        if not account:
            flash("존재하지 않는 계정입니다.")
            return redirect(url_for("admin_login"))

        if str(account.get("password")) != admin_pw:
            flash("비밀번호가 올바르지 않습니다.")
            return redirect(url_for("admin_login"))

        if int(account.get("is_active", 0)) != 1:
            flash("비활성화된 계정입니다.")
            return redirect(url_for("admin_login"))

        if account.get("role") not in ["seller", "admin"]:
            flash("판매자/관리자 계정만 로그인할 수 있습니다.")
            return redirect(url_for("admin_login"))

        session["role"] = account.get("role")
        session["account_id"] = account.get("account_id")
        session["login_id"] = account.get("login_id")

        if account.get("seller_id"):
            session["seller_id"] = account.get("seller_id")
        else:
            seller = get_first_available_seller()
            session["seller_id"] = seller["seller_id"]

        flash("로그인 성공")
        return redirect(url_for("seller_dashboard"))

    finally:
        conn.close()


@app.route("/admin/logout")
def admin_logout():
    session.pop("account_id", None)
    session.pop("seller_id", None)
    session.pop("role", None)
    session.pop("login_id", None)
    return redirect(url_for("admin_login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        user_pw = request.form.get("user_pw", "").strip()
        user_name = request.form.get("user_name", "").strip()
        gender = request.form.get("gender", "").strip()
        height = request.form.get("height", type=int)
        weight = request.form.get("weight", type=int)
        size = request.form.get("size", "").strip()
        preferred_fit = request.form.get("preferred_fit", "").strip()

        if not user_id or not user_pw or not user_name:
            flash("필수 정보를 입력해주세요.")
            return redirect(url_for("signup"))

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE username=%s", (user_id,))
                exists = cursor.fetchone()

                if exists:
                    flash("이미 사용 중인 아이디입니다.")
                    return redirect(url_for("signup"))

                cursor.execute(
                    """
                    INSERT INTO users
                    (username, password, gender, height, weight, preferred_fit, usual_size)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        user_pw,
                        gender,
                        height,
                        weight,
                        preferred_fit,
                        size,
                    ),
                )
                conn.commit()
        finally:
            conn.close()

        return "<script>alert('회원가입 완료!'); location.href='/login';</script>"

    return render_template("signup.html")


@app.route("/main", methods=["GET", "POST"])
def main_page():
    search_query = request.args.get("search", "").strip().lower()
    current_cate = request.args.get("cate", "ALL")
    user_name = session.get("user_name")

    items = get_all_products()
    display_items = items

    category_map = {
        "TOP": "상의",
        "PANTS": "하의",
        "OUTER": "아우터",
        "SHOES": "신발"
    }

    if request.method == "POST":
        file = request.files.get("search_img")
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_DIR, filename)
            file.save(save_path)

            try:
                from search import search_similar_images
                image_results = search_similar_images(save_path, top_k=5)
                display_items = match_products_from_image_results(image_results, items)

                if not display_items:
                    flash("유사한 상품을 찾지 못했습니다. 배경이 단순한 대표 이미지를 다시 올려보세요.")

                return render_template(
                    "main.html",
                    items=display_items,
                    user_name=user_name,
                    current_cate="AI 이미지 검색 결과"
                )
            except Exception as e:
                flash(f"이미지 검색 중 오류: {e}")

    if current_cate != "ALL":
        target_db_value = category_map.get(current_cate, current_cate)
        display_items = [
            p for p in items
            if str(p.get("category")).strip() == target_db_value
        ]

    if search_query:
        display_items = [
            p for p in display_items
            if search_query in p["name"].lower() or search_query in p["brand"].lower()
        ]
        current_cate = f"'{search_query}' 검색 결과"

    return render_template(
        "main.html",
        items=display_items,
        user_name=user_name,
        current_cate=current_cate
    )


@app.route("/product/<int:p_id>")
def product_detail(p_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            product_sql = """
                SELECT
                    product_id AS id,
                    product_name AS name,
                    price,
                    description AS `desc`,
                    brand_name AS brand,
                    image_main1 AS img,
                    size AS size_options
                FROM products
                WHERE product_id = %s
            """
            cur.execute(product_sql, (p_id,))
            row = cur.fetchone()

            if not row:
                return "<script>alert('상품을 찾을 수 없습니다.'); history.back();</script>"

            product = {
                "id": row.get("id"),
                "name": row.get("name"),
                "price": _safe_int(row.get("price")),
                "desc": row.get("desc") or "",
                "brand": row.get("brand") or "",
                "img": row.get("img") or "",
                "size_options": row.get("size_options") or "",
            }

            review_sql = """
                SELECT
                    u.username,
                    r.created_at,
                    r.purchased_size,
                    r.rating,
                    r.size_feel,
                    u.height,
                    u.weight,
                    r.review_text
                FROM reviews r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.product_id = %s
                ORDER BY r.created_at DESC
            """
            cur.execute(review_sql, (p_id,))
            review_rows = cur.fetchall()

            reviews = []
            for r in review_rows:
                reviews.append({
                    "username": r.get("username"),
                    "created_at": r.get("created_at").strftime("%Y-%m-%d") if r.get("created_at") else "",
                    "purchased_size": r.get("purchased_size"),
                    "rating": r.get("rating"),
                    "size_feel": r.get("size_feel"),
                    "height": r.get("height"),
                    "weight": r.get("weight"),
                    "review_text": r.get("review_text"),
                })

            recommendation = None
            can_review = False

            user_id = session.get("user_id")
            if user_id:
                can_review = has_purchased_product(user_id, p_id)

                cur.execute("SELECT height, weight FROM users WHERE user_id = %s", (user_id,))
                u_info = cur.fetchone()

                if u_info:
                    u_h = u_info.get("height")
                    u_w = u_info.get("weight")

                    if u_h and u_w:
                        rec_sql = """
                            SELECT r.purchased_size, COUNT(*) as cnt
                            FROM reviews r
                            JOIN users u ON r.user_id = u.user_id
                            WHERE r.product_id = %s
                              AND u.height BETWEEN %s-3 AND %s+3
                              AND u.weight BETWEEN %s-3 AND %s+3
                            GROUP BY r.purchased_size
                            ORDER BY cnt DESC
                            LIMIT 1
                        """
                        cur.execute(rec_sql, (p_id, u_h, u_h, u_w, u_w))
                        rec_row = cur.fetchone()

                        if rec_row:
                            recommendation = {
                                "recommended_size": rec_row.get("purchased_size"),
                                "message": "고객님과 비슷한 체형의 사용자들이 가장 많이 선택한 사이즈입니다.",
                                "match_count": rec_row.get("cnt"),
                            }

        return render_template(
            "detail.html",
            p=product,
            reviews=reviews,
            recommendation=recommendation,
            can_review=can_review
        )

    except Exception as e:
        print(f"Error detail: {e}")
        return "<script>alert('상품 상세 조회 중 오류가 발생했습니다.'); history.back();</script>"
    finally:
        conn.close()


@app.route("/init-demo")
def init_demo():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            cursor.execute("TRUNCATE TABLE reviews")
            cursor.execute("TRUNCATE TABLE users")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")

            demo_users = [
                ("insu", "1234", "남", 173, 68, "세미오버핏", "M"),
                ("minho", "1234", "남", 172, 67, "세미오버핏", "M"),
                ("jinho", "1234", "남", 174, 70, "세미오버핏", "M"),
                ("hyun", "1234", "남", 173, 66, "세미오버핏", "M"),
                ("taeho", "1234", "남", 173, 68, "세미오버핏", "M"),
                ("jun", "1234", "남", 172, 65, "세미오버핏", "M"),
                ("woojin", "1234", "남", 176, 72, "오버핏", "L"),
                ("seong", "1234", "남", 170, 64, "정핏", "S"),
                ("yong", "1234", "남", 174, 68, "세미오버핏", "M"),
                ("dong", "1234", "남", 172, 67, "세미오버핏", "M"),
                ("jiwon", "1234", "여", 162, 52, "오버핏", "L"),
                ("hojun", "1234", "남", 178, 75, "오버핏", "L"),
                ("minseok", "1234", "남", 173, 69, "세미오버핏", "M"),
            ]

            for u in demo_users:
                cursor.execute(
                    """
                    INSERT INTO users
                    (username, password, gender, height, weight, preferred_fit, usual_size)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    u,
                )

            conn.commit()

        flash("데모 유저 데이터 삽입 완료!")
        return redirect(url_for("login"))
    finally:
        conn.close()


@app.route("/review/create/<int:product_id>", methods=["GET", "POST"])
def review_create(product_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("리뷰 작성을 위해 로그인하세요.")
        return redirect(url_for("login"))

    product = get_product_by_id(product_id)
    if not product:
        flash("상품을 찾을 수 없습니다.")
        return redirect(url_for("main_page"))

    if not has_purchased_product(user_id, product_id):
        flash("이 상품을 주문한 회원만 리뷰를 작성할 수 있습니다.")
        return redirect(url_for("product_detail", p_id=product_id))

    if has_existing_review(user_id, product_id):
        flash("이미 이 상품에 리뷰를 작성하셨습니다.")
        return redirect(url_for("product_detail", p_id=product_id))

    if request.method == "GET":
        return render_template("review_form.html", product=product)

    purchased_size = request.form.get("purchased_size")
    size_feel = request.form.get("size_feel")
    fit_feel = request.form.get("fit_feel")
    rating = request.form.get("rating")
    review_text = request.form.get("review_text")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO reviews (
                    user_id, product_id, purchased_size,
                    size_feel, fit_feel, rating, review_text, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cur.execute(sql, (
                user_id, product_id, purchased_size,
                size_feel, fit_feel, rating, review_text
            ))
        conn.commit()
        flash("리뷰가 성공적으로 등록되었습니다!")
    except Exception as e:
        conn.rollback()
        flash(f"리뷰 등록 중 오류 발생: {e}")
        return redirect(url_for("review_create", product_id=product_id))
    finally:
        conn.close()

    return redirect(url_for("product_detail", p_id=product_id))


@app.route("/add_cart/<int:p_id>")
def add_cart(p_id):
    action = request.args.get("action")
    product = get_product_by_id(p_id)

    if product:
        cart = session.get("cart", {})
        p_id_str = str(p_id)

        if p_id_str in cart:
            cart[p_id_str]["qty"] += 1
        else:
            cart[p_id_str] = {
                "name": product["name"],
                "price": product["price"],
                "brand": product["brand"],
                "img": product.get("img", ""),
                "qty": 1,
                "selected_size": "",
                "selected_color": product.get("color", ""),
            }

        session["cart"] = cart
        session.modified = True

    if action == "buy":
        return redirect(url_for("order_page", p_id=p_id))

    return redirect(url_for("cart_page"))


@app.route("/update_cart/<int:p_id>/<string:action>")
def update_cart(p_id, action):
    cart = session.get("cart", {})
    p_id_str = str(p_id)

    if p_id_str in cart:
        if action == "plus":
            cart[p_id_str]["qty"] += 1
        elif action == "minus":
            cart[p_id_str]["qty"] -= 1
            if cart[p_id_str]["qty"] <= 0:
                cart.pop(p_id_str)
        elif action == "delete":
            cart.pop(p_id_str)

        session["cart"] = cart
        session.modified = True

    return redirect(url_for("cart_page"))


@app.route("/cart")
def cart_page():
    cart_dict = session.get("cart", {})
    cart_items = []
    total_price = 0

    for key, item in cart_dict.items():
        copied = dict(item)
        copied["id"] = key
        cart_items.append(copied)
        total_price += copied["price"] * copied["qty"]

    return render_template("cart.html", items=cart_items, total=total_price)


@app.route("/order")
@app.route("/order/<int:p_id>")
def order_page(p_id=None):
    if p_id is not None:
        product = get_product_by_id(p_id)
        if product:
            return render_template("order.html", p=product, product=product)
        return "상품을 찾을 수 없습니다.", 404

    cart = session.get("cart")
    if not cart:
        flash("장바구니가 비어있습니다.")
        return redirect(url_for("main_page"))

    return render_template("order.html")


@app.route("/order_complete", methods=["POST"])
def order_complete():
    user_id = session.get("user_id")
    if not user_id:
        return "<script>alert('로그인이 필요합니다.'); location.href='/login';</script>"

    p_id = request.form.get("p_id")
    qty = request.form.get("qty", 1, type=int)
    cart = session.get("cart", {})

    if not cart and not p_id:
        return "<script>alert('주문할 상품 정보가 없습니다.'); location.href='/main';</script>"

    items_to_order = []

    if p_id:
        product = get_product_by_id(int(p_id))
        if product:
            selected_size = request.form.get("selected_size", "").strip()
            selected_color = request.form.get("selected_color", "").strip() or product.get("color", "")

            if not selected_size:
                size_options = [s.strip() for s in (product.get("size_options") or "").split(",") if s.strip()]
                selected_size = size_options[0] if size_options else ""

            items_to_order.append({
                "p_id": int(p_id),
                "price": _safe_int(product["price"]),
                "qty": qty,
                "seller_id": product.get("seller_id"),
                "selected_size": selected_size,
                "selected_color": selected_color,
            })
    else:
        for p_id_str, item in cart.items():
            product = get_product_by_id(int(p_id_str))
            if not product:
                continue

            selected_size = item.get("selected_size", "").strip()
            selected_color = item.get("selected_color", "").strip() or product.get("color", "")

            if not selected_size:
                size_options = [s.strip() for s in (product.get("size_options") or "").split(",") if s.strip()]
                selected_size = size_options[0] if size_options else ""

            items_to_order.append({
                "p_id": int(p_id_str),
                "price": _safe_int(item.get("price", 0)),
                "qty": _safe_int(item.get("qty", 1)),
                "seller_id": product.get("seller_id"),
                "selected_size": selected_size,
                "selected_color": selected_color,
            })

    receiver = request.form.get("receiver", "").strip()
    phone = request.form.get("phone", "").strip()
    customer_email = request.form.get("email", "").strip()
    address1 = request.form.get("address1", "").strip()
    address2 = request.form.get("address2", "").strip()
    address = f"{address1} {address2}".strip()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for item in items_to_order:
                order_code = f"ORD-{user_id}-{int(time.time())}-{item['p_id']}"
                total_amount = _safe_int(item["price"]) * _safe_int(item["qty"])

                try:
                    sql_order = """
                        INSERT INTO orders
                        (order_code, seller_id, user_id, customer_name,
                         customer_phone, customer_email, address, total_amount, order_status, order_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '신규주문', NOW())
                    """
                    cursor.execute(sql_order, (
                        order_code,
                        item["seller_id"],
                        user_id,
                        receiver,
                        phone,
                        customer_email,
                        address,
                        total_amount,
                    ))
                except Exception:
                    sql_order = """
                        INSERT INTO orders
                        (order_code, seller_id, user_id, customer_name,
                         customer_phone, address, total_amount, order_status, order_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, '신규주문', NOW())
                    """
                    cursor.execute(sql_order, (
                        order_code,
                        item["seller_id"],
                        user_id,
                        receiver,
                        phone,
                        address,
                        total_amount,
                    ))

                order_id = cursor.lastrowid

                sql_item = """
                    INSERT INTO order_items
                    (order_id, product_id, quantity, unit_price, subtotal, selected_size, selected_color)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_item, (
                    order_id,
                    item["p_id"],
                    item["qty"],
                    item["price"],
                    total_amount,
                    item["selected_size"],
                    item["selected_color"],
                ))

            conn.commit()

        if not p_id:
            session.pop("cart", None)

        return render_template("complete.html")

    except Exception as e:
        conn.rollback()
        print(f"❌ 주문 에러: {e}")
        return f"<script>alert('주문 실패: {e}'); history.back();</script>"
    finally:
        conn.close()


@app.route("/mypage")
def mypage():
    user_id = session.get("user_id")
    if not user_id:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            user = cursor.fetchone()

            cursor.execute(
                """
                SELECT o.order_id,
                       oi.product_id,
                       o.order_date,
                       p.product_name AS name,
                       oi.subtotal AS price,
                       o.order_status AS status
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                JOIN products p ON oi.product_id = p.product_id
                WHERE o.user_id = %s
                ORDER BY o.order_date DESC
                """,
                (user_id,),
            )
            orders = cursor.fetchall()
    finally:
        conn.close()

    cart = session.get("cart", {})
    return render_template("mypage.html", user=user, cart=cart, orders=orders)


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

    conn = get_connection()
    try:
        if request.method == "POST":
            gender = request.form.get("gender", "").strip()
            height = request.form.get("height", type=int)
            weight = request.form.get("weight", type=int)
            preferred_fit = request.form.get("preferred_fit", "").strip()
            usual_size = request.form.get("size", "").strip()

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET gender=%s, height=%s, weight=%s,
                        preferred_fit=%s, usual_size=%s
                    WHERE user_id=%s
                    """,
                    (gender, height, weight, preferred_fit, usual_size, user_id),
                )
                conn.commit()

            flash("정보가 수정되었습니다.")
            return redirect(url_for("mypage"))

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            user = cursor.fetchone()
    finally:
        conn.close()

    return render_template("edit_profile.html", user=user)


@app.route("/cs/create", methods=["GET", "POST"])
def cs_create():
    user_id = session.get("user_id")
    if not user_id:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

    if request.method == "GET":
        o_id = request.args.get("order_id")
        p_id = request.args.get("product_id")

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT product_id, product_name, seller_id, image_main1 AS img
                    FROM products
                    WHERE product_id=%s
                """
                cur.execute(sql, (p_id,))
                product = cur.fetchone()
        finally:
            conn.close()

        return render_template("cs_form.html", o_id=o_id, p_id=p_id, product=product)

    o_id = request.form.get("order_id")
    p_id = request.form.get("product_id")
    s_id = request.form.get("seller_id")
    cs_type = request.form.get("cs_type")
    title = request.form.get("cs_title")
    content = request.form.get("cs_content")

    final_o_id = int(o_id) if o_id and o_id != "None" and o_id != "0" else None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO customer_service
                (order_id, product_id, seller_id, customer_name, cs_type, cs_title, cs_content, cs_status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, '접수', NOW())
            """
            cur.execute(sql, (
                final_o_id,
                p_id,
                s_id,
                session.get("user_name"),
                cs_type,
                title,
                content
            ))
            conn.commit()
    finally:
        conn.close()

    return redirect(url_for("cs_list"))


@app.route("/cs/list")
def cs_list():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cs.*, p.product_name
                FROM customer_service cs
                JOIN products p ON cs.product_id = p.product_id
                WHERE cs.customer_name = %s
                ORDER BY cs.created_at DESC
            """, (session.get("user_name"),))
            cs_items = cur.fetchall()
    finally:
        conn.close()

    return render_template("cs_list.html", cs_items=cs_items)


@app.route("/cs/detail/<int:cs_id>")
def cs_detail(cs_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cs.*, p.product_name
                FROM customer_service cs
                JOIN products p ON cs.product_id = p.product_id
                WHERE cs_id = %s
            """, (cs_id,))
            cs_data = cur.fetchone()
    finally:
        conn.close()

    return render_template("cs_detail.html", cs=cs_data)


# =========================
# 판매자 홈 / 대시보드
# =========================
@app.route("/seller/home")
def seller_home():
    sellers = get_sellers_for_home()
    try:
        return render_template("home.html", sellers=sellers)
    except TemplateNotFound:
        return """
        <html><body style="font-family:sans-serif;padding:40px;">
        <h1>판매자 홈</h1>
        <p>home.html 템플릿이 없습니다.</p>
        <a href="/admin/login">관리자 로그인</a>
        </body></html>
        """


@app.route("/seller/select/<int:seller_id>")
def seller_select(seller_id):
    session["seller_id"] = seller_id
    session["role"] = "seller"
    flash(f"{seller_id}번 판매자로 접속했습니다.")
    return redirect(url_for("seller_dashboard"))


@app.route("/seller/dashboard")
def seller_dashboard():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    data = get_dashboard_data(seller["seller_id"])

    return render_template(
        "seller_dashboard.html",
        seller=seller,
        today_sales=data["today_sales"],
        month_sales=data["month_sales"],
        pending_orders=data["pending_orders"],
        cs_count=data["cs_count"],
        top_products=data["top_products"],
        low_stock_products=data["low_stock_products"],
        recent_orders=data["recent_orders"],
        chart_labels=data["chart_labels"],
        chart_values=data["chart_values"],
        monthly_labels=data["monthly_labels"],
        monthly_values=data["monthly_values"],
    )


# =========================
# 판매자 매출 관리
# =========================
@app.route("/seller/sales")
def seller_sales():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    start_date = request.args.get("start_date", _days_ago_str(29))
    end_date = request.args.get("end_date", _today_str())
    year = request.args.get("year", str(datetime.now().year))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_amount), 0) AS total_sales,
                    COUNT(*) AS total_orders
                FROM orders
                WHERE seller_id = %s
            """, (seller["seller_id"],))
            summary = cur.fetchone() or {}
            total_sales = _safe_int(summary.get("total_sales"))
            total_orders = _safe_int(summary.get("total_orders"))
            avg_order = int(total_sales / total_orders) if total_orders > 0 else 0

            cur.execute("""
                SELECT
                    DATE(order_date) AS d,
                    COALESCE(SUM(total_amount), 0) AS sales
                FROM orders
                WHERE seller_id = %s
                  AND DATE(order_date) BETWEEN %s AND %s
                GROUP BY DATE(order_date)
                ORDER BY d ASC
            """, (seller["seller_id"], start_date, end_date))
            daily_sales = cur.fetchall()

            cur.execute("""
                SELECT
                    YEAR(order_date) AS y,
                    MONTH(order_date) AS month_num,
                    DATE_FORMAT(order_date, '%%m월') AS m,
                    COALESCE(SUM(total_amount), 0) AS sales
                FROM orders
                WHERE seller_id = %s
                  AND YEAR(order_date) = %s
                GROUP BY YEAR(order_date), MONTH(order_date), DATE_FORMAT(order_date, '%%m월')
                ORDER BY month_num ASC
            """, (seller["seller_id"], year))
            monthly_sales = cur.fetchall()

            cur.execute("""
                SELECT
                    YEAR(order_date) AS y,
                    COALESCE(SUM(total_amount), 0) AS sales
                FROM orders
                WHERE seller_id = %s
                GROUP BY YEAR(order_date)
                ORDER BY y ASC
            """, (seller["seller_id"],))
            yearly_sales = cur.fetchall()

            cur.execute("""
                SELECT DISTINCT YEAR(order_date) AS y
                FROM orders
                WHERE seller_id = %s
                ORDER BY y DESC
            """, (seller["seller_id"],))
            year_rows = cur.fetchall()
            year_list = [r.get("y") for r in year_rows] or [datetime.now().year]

    finally:
        conn.close()

    daily_labels = [str(r.get("d")) for r in daily_sales]
    daily_values = [_safe_int(r.get("sales")) for r in daily_sales]

    monthly_labels = [r.get("m") for r in monthly_sales]
    monthly_values = [_safe_int(r.get("sales")) for r in monthly_sales]

    yearly_labels = [str(r.get("y")) for r in yearly_sales]
    yearly_values = [_safe_int(r.get("sales")) for r in yearly_sales]

    return render_template(
        "seller_sales.html",
        seller=seller,
        total_sales=total_sales,
        total_orders=total_orders,
        avg_order=avg_order,
        start_date=start_date,
        end_date=end_date,
        year=year,
        year_list=year_list,
        daily_sales=daily_sales,
        monthly_sales=monthly_sales,
        yearly_sales=yearly_sales,
        daily_labels=_json_dump(daily_labels),
        daily_values=_json_dump(daily_values),
        monthly_labels=_json_dump(monthly_labels),
        monthly_values=_json_dump(monthly_values),
        yearly_labels=_json_dump(yearly_labels),
        yearly_values=_json_dump(yearly_values),
    )


@app.route("/seller/sales/export/daily")
def export_sales_csv():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    start_date = request.args.get("start_date", _days_ago_str(29))
    end_date = request.args.get("end_date", _today_str())

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DATE(order_date) AS d, COALESCE(SUM(total_amount), 0) AS sales
                FROM orders
                WHERE seller_id = %s
                  AND DATE(order_date) BETWEEN %s AND %s
                GROUP BY DATE(order_date)
                ORDER BY d ASC
            """, (seller["seller_id"], start_date, end_date))
            rows = cur.fetchall()
    finally:
        conn.close()

    return _csv_response(
        "daily_sales.csv",
        ["날짜", "매출"],
        [[r.get("d"), _safe_int(r.get("sales"))] for r in rows]
    )


@app.route("/seller/sales/export/month")
def export_month_sales_csv():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    year = request.args.get("year", str(datetime.now().year))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DATE_FORMAT(order_date, '%%m월') AS m, COALESCE(SUM(total_amount), 0) AS sales
                FROM orders
                WHERE seller_id = %s
                  AND YEAR(order_date) = %s
                GROUP BY YEAR(order_date), MONTH(order_date), DATE_FORMAT(order_date, '%%m월')
                ORDER BY MONTH(order_date) ASC
            """, (seller["seller_id"], year))
            rows = cur.fetchall()
    finally:
        conn.close()

    return _csv_response(
        f"monthly_sales_{year}.csv",
        ["월", "매출"],
        [[r.get("m"), _safe_int(r.get("sales"))] for r in rows]
    )


@app.route("/seller/sales/export/year")
def export_year_sales_csv():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT YEAR(order_date) AS y, COALESCE(SUM(total_amount), 0) AS sales
                FROM orders
                WHERE seller_id = %s
                GROUP BY YEAR(order_date)
                ORDER BY y ASC
            """, (seller["seller_id"],))
            rows = cur.fetchall()
    finally:
        conn.close()

    return _csv_response(
        "yearly_sales.csv",
        ["연도", "매출"],
        [[r.get("y"), _safe_int(r.get("sales"))] for r in rows]
    )


# =========================
# 판매자 상품 관리
# =========================
@app.route("/seller/products")
def seller_products():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    page = request.args.get("page", 1, type=int)
    per_page = 10
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "전체").strip()
    sort = request.args.get("sort", "latest").strip()

    where_clauses = ["seller_id = %s"]
    params = [seller["seller_id"]]

    if keyword:
        where_clauses.append("(product_name LIKE %s OR product_code LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if status != "전체":
        where_clauses.append("status = %s")
        params.append(status)

    order_by_map = {
        "latest": "product_id DESC",
        "product_code_asc": "product_code ASC",
        "product_code_desc": "product_code DESC",
        "brand_name_asc": "brand_name ASC",
        "brand_name_desc": "brand_name DESC",
        "product_name_asc": "product_name ASC",
        "product_name_desc": "product_name DESC",
        "category_asc": "category1 ASC",
        "category_desc": "category1 DESC",
        "price_asc": "price ASC",
        "price_desc": "price DESC",
        "stock_asc": "stock ASC",
        "stock_desc": "stock DESC",
    }
    order_by = order_by_map.get(sort, "product_id DESC")

    where_sql = " AND ".join(where_clauses)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) AS cnt
                FROM products
                WHERE {where_sql}
            """, tuple(params))
            total_count = _safe_int(cur.fetchone().get("cnt"))
            total_pages = max(1, math.ceil(total_count / per_page))
            offset = (page - 1) * per_page

            cur.execute(f"""
                SELECT *
                FROM products
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT %s OFFSET %s
            """, tuple(params + [per_page, offset]))
            rows = cur.fetchall()
            products = [_merge_product_row(r) for r in rows]
    finally:
        conn.close()

    return render_template(
        "seller_products.html",
        seller=seller,
        products=products,
        keyword=keyword,
        status=status,
        sort=sort,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@app.route("/seller/product/add", methods=["GET", "POST"])
def add_product():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()

    if request.method == "GET":
        return render_template(
            "product_form.html",
            mode="add",
            seller=seller,
            product=None
        )

    product_code = request.form.get("product_code", "").strip()
    product_name = request.form.get("product_name", "").strip()
    category1 = request.form.get("category1", "").strip()
    category2 = request.form.get("category2", "").strip()
    gender = request.form.get("gender", "").strip()
    price = request.form.get("price", type=int) or 0
    color = request.form.get("color", "").strip()
    size = request.form.get("size", "").strip()
    stock = request.form.get("stock", type=int) or 0
    status = request.form.get("status", "").strip()
    description = request.form.get("description", "").strip()

    image_main1 = save_uploaded_file(request.files.get("image_main1"))
    image_main2 = save_uploaded_file(request.files.get("image_main2"))
    image_main3 = save_uploaded_file(request.files.get("image_main3"))
    image_detail = save_uploaded_file(request.files.get("image_detail"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO products
                (
                    seller_id, product_code, brand_name, product_name,
                    category1, category2, gender,
                    price, color, size, stock, status,
                    description, image_main1, image_main2, image_main3, image_detail
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                seller["seller_id"],
                product_code,
                seller.get("brand_name", ""),
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
            ))
            conn.commit()

        flash("상품이 등록되었습니다.")
        return redirect(url_for("seller_products"))
    except Exception as e:
        conn.rollback()
        flash(f"상품 등록 중 오류: {e}")
        return redirect(url_for("add_product"))
    finally:
        conn.close()


@app.route("/seller/product/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    product = get_product_by_id(product_id)

    if not product or product.get("seller_id") != seller["seller_id"]:
        flash("상품 정보를 찾을 수 없습니다.")
        return redirect(url_for("seller_products"))

    if request.method == "GET":
        return render_template(
            "product_form.html",
            mode="edit",
            seller=seller,
            product=product
        )

    product_code = request.form.get("product_code", "").strip()
    product_name = request.form.get("product_name", "").strip()
    category1 = request.form.get("category1", "").strip()
    category2 = request.form.get("category2", "").strip()
    gender = request.form.get("gender", "").strip()
    price = request.form.get("price", type=int) or 0
    color = request.form.get("color", "").strip()
    size = request.form.get("size", "").strip()
    stock = request.form.get("stock", type=int) or 0
    status = request.form.get("status", "").strip()
    description = request.form.get("description", "").strip()

    image_main1 = save_uploaded_file(request.files.get("image_main1"))
    image_main2 = save_uploaded_file(request.files.get("image_main2"))
    image_main3 = save_uploaded_file(request.files.get("image_main3"))
    image_detail = save_uploaded_file(request.files.get("image_detail"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                UPDATE products
                SET product_code=%s,
                    product_name=%s,
                    category1=%s,
                    category2=%s,
                    gender=%s,
                    price=%s,
                    color=%s,
                    size=%s,
                    stock=%s,
                    status=%s,
                    description=%s
            """
            params = [
                product_code, product_name, category1, category2, gender,
                price, color, size, stock, status, description
            ]

            if image_main1:
                sql += ", image_main1=%s"
                params.append(image_main1)
            if image_main2:
                sql += ", image_main2=%s"
                params.append(image_main2)
            if image_main3:
                sql += ", image_main3=%s"
                params.append(image_main3)
            if image_detail:
                sql += ", image_detail=%s"
                params.append(image_detail)

            sql += " WHERE product_id=%s AND seller_id=%s"
            params.extend([product_id, seller["seller_id"]])

            cur.execute(sql, tuple(params))
            conn.commit()

        flash("상품이 수정되었습니다.")
        return redirect(url_for("seller_products"))
    except Exception as e:
        conn.rollback()
        flash(f"상품 수정 중 오류: {e}")
        return redirect(url_for("edit_product", product_id=product_id))
    finally:
        conn.close()


@app.route("/seller/products/delete", methods=["POST"])
def delete_selected_products():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    product_ids = request.form.getlist("product_ids")

    if not product_ids:
        flash("삭제할 상품을 선택하세요.")
        return redirect(url_for("seller_products"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(product_ids))
            sql = f"""
                DELETE FROM products
                WHERE seller_id = %s
                  AND product_id IN ({placeholders})
            """
            cur.execute(sql, tuple([seller["seller_id"]] + product_ids))
            conn.commit()

        flash("선택한 상품이 삭제되었습니다.")
    except Exception as e:
        conn.rollback()
        flash(f"상품 삭제 중 오류: {e}")
    finally:
        conn.close()

    return redirect(url_for("seller_products"))


@app.route("/seller/product/<int:product_id>/stock", methods=["POST"])
def update_product_stock(product_id):
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    stock = request.form.get("stock", type=int)
    seller = get_current_seller()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE products
                SET stock = %s
                WHERE product_id = %s
                  AND seller_id = %s
            """, (stock, product_id, seller["seller_id"]))
            conn.commit()

        flash("재고가 수정되었습니다.")
    except Exception as e:
        conn.rollback()
        flash(f"재고 수정 중 오류: {e}")
    finally:
        conn.close()

    return redirect(url_for("seller_dashboard"))


# =========================
# 판매자 주문 관리
# =========================
@app.route("/seller/orders")
def seller_orders():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()

    page = request.args.get("page", 1, type=int)
    per_page = 10
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "전체").strip()
    sort = request.args.get("sort", "latest").strip()
    type_filter = request.args.get("type", "").strip()

    where_clauses = ["o.seller_id = %s"]
    params = [seller["seller_id"]]

    if keyword:
        where_clauses.append("o.order_code LIKE %s")
        params.append(f"%{keyword}%")

    if status and status != "전체":
        where_clauses.append("o.order_status = %s")
        params.append(status)

    if type_filter == "pending":
        where_clauses.append("o.order_status IN ('신규주문', '배송준비중')")

    order_map = {
        "latest": "o.order_date DESC",
        "price_desc": "o.total_amount DESC",
        "price_asc": "o.total_amount ASC",
        "order_date_asc": "o.order_date ASC",
        "order_date_desc": "o.order_date DESC",
        "status_asc": "o.order_status ASC",
        "status_desc": "o.order_status DESC",
        "customer_name_asc": "o.customer_name ASC",
        "customer_name_desc": "o.customer_name DESC",
        "customer_email_asc": "o.customer_email ASC",
        "customer_email_desc": "o.customer_email DESC",
        "customer_phone_asc": "o.customer_phone ASC",
        "customer_phone_desc": "o.customer_phone DESC",
        "address_asc": "o.address ASC",
        "address_desc": "o.address DESC",
    }
    order_by = order_map.get(sort, "o.order_date DESC")
    where_sql = " AND ".join(where_clauses)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            count_sql = f"""
                SELECT COUNT(*) AS cnt
                FROM orders o
                WHERE {where_sql}
            """
            cur.execute(count_sql, tuple(params))
            total_count = _safe_int(cur.fetchone().get("cnt"))
            total_pages = max(1, math.ceil(total_count / per_page))
            offset = (page - 1) * per_page

            try:
                list_sql = f"""
                    SELECT
                        o.order_id,
                        o.order_code,
                        o.customer_name,
                        o.customer_email,
                        o.customer_phone,
                        o.address,
                        DATE_FORMAT(o.order_date, '%%Y-%%m-%%d %%H:%%i') AS order_date,
                        o.total_amount,
                        o.order_status
                    FROM orders o
                    WHERE {where_sql}
                    ORDER BY {order_by}
                    LIMIT %s OFFSET %s
                """
                cur.execute(list_sql, tuple(params + [per_page, offset]))
            except Exception:
                list_sql = f"""
                    SELECT
                        o.order_id,
                        o.order_code,
                        o.customer_name,
                        '' AS customer_email,
                        o.customer_phone,
                        o.address,
                        DATE_FORMAT(o.order_date, '%%Y-%%m-%%d %%H:%%i') AS order_date,
                        o.total_amount,
                        o.order_status
                    FROM orders o
                    WHERE {where_sql}
                    ORDER BY {order_by}
                    LIMIT %s OFFSET %s
                """
                cur.execute(list_sql, tuple(params + [per_page, offset]))

            orders = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "seller_orders.html",
        seller=seller,
        orders=orders,
        total_count=total_count,
        total_pages=total_pages,
        page=page
    )


@app.route("/seller/orders/<int:order_id>")
def seller_order_detail(order_id):
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT
                        o.order_id,
                        o.order_code,
                        o.customer_name,
                        o.customer_email,
                        o.customer_phone,
                        o.address,
                        DATE_FORMAT(o.order_date, '%%Y-%%m-%%d %%H:%%i') AS order_date,
                        o.total_amount,
                        o.order_status
                    FROM orders o
                    WHERE o.order_id = %s
                      AND o.seller_id = %s
                """, (order_id, seller["seller_id"]))
            except Exception:
                cur.execute("""
                    SELECT
                        o.order_id,
                        o.order_code,
                        o.customer_name,
                        '' AS customer_email,
                        o.customer_phone,
                        o.address,
                        DATE_FORMAT(o.order_date, '%%Y-%%m-%%d %%H:%%i') AS order_date,
                        o.total_amount,
                        o.order_status
                    FROM orders o
                    WHERE o.order_id = %s
                      AND o.seller_id = %s
                """, (order_id, seller["seller_id"]))

            order = cur.fetchone()

            if not order:
                flash("주문 정보를 찾을 수 없습니다.")
                return redirect(url_for("seller_orders"))

            cur.execute("""
                SELECT
                    oi.order_item_id,
                    oi.product_id,
                    p.product_code,
                    p.product_name,
                    p.image_main1,
                    oi.quantity,
                    oi.unit_price,
                    oi.subtotal,
                    oi.selected_size,
                    oi.selected_color
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                WHERE oi.order_id = %s
                ORDER BY oi.order_item_id ASC
            """, (order_id,))
            order_items = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "seller_order_detail.html",
        seller=seller,
        order=order,
        order_items=order_items
    )


@app.route("/seller/orders/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    new_status = request.form.get("order_status", "").strip()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE orders
                SET order_status = %s
                WHERE order_id = %s
                  AND seller_id = %s
            """, (new_status, order_id, seller["seller_id"]))
            conn.commit()

        flash("주문 상태가 변경되었습니다.")
    except Exception as e:
        conn.rollback()
        flash(f"주문 상태 변경 중 오류: {e}")
    finally:
        conn.close()

    return redirect(request.referrer or url_for("seller_orders"))


# =========================
# 판매자 CS 관리
# =========================
@app.route("/seller/cs")
def seller_cs():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()

    page_q = request.args.get("page_q", 1, type=int)
    page_r = request.args.get("page_r", 1, type=int)
    per_page = 10

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) AS cnt
                FROM customer_service
                WHERE seller_id = %s
                  AND cs_type = '상품문의'
            """, (seller["seller_id"],))
            total_q = _safe_int(cur.fetchone().get("cnt"))
            total_pages_q = max(1, math.ceil(total_q / per_page))
            offset_q = (page_q - 1) * per_page

            cur.execute("""
                SELECT
                    cs.cs_id,
                    cs.customer_name,
                    p.product_name,
                    cs.cs_title,
                    cs.cs_content,
                    cs.cs_reply,
                    cs.cs_status
                FROM customer_service cs
                JOIN products p ON cs.product_id = p.product_id
                WHERE cs.seller_id = %s
                  AND cs.cs_type = '상품문의'
                ORDER BY cs.created_at DESC
                LIMIT %s OFFSET %s
            """, (seller["seller_id"], per_page, offset_q))
            questions = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*) AS cnt
                FROM customer_service
                WHERE seller_id = %s
                  AND cs_type IN ('교환요청', '반품요청')
            """, (seller["seller_id"],))
            total_r = _safe_int(cur.fetchone().get("cnt"))
            total_pages_r = max(1, math.ceil(total_r / per_page))
            offset_r = (page_r - 1) * per_page

            cur.execute("""
                SELECT
                    cs.cs_id,
                    o.order_code,
                    cs.customer_name,
                    p.product_name,
                    cs.cs_type,
                    cs.cs_content,
                    cs.cs_status
                FROM customer_service cs
                LEFT JOIN orders o ON cs.order_id = o.order_id
                JOIN products p ON cs.product_id = p.product_id
                WHERE cs.seller_id = %s
                  AND cs.cs_type IN ('교환요청', '반품요청')
                ORDER BY cs.created_at DESC
                LIMIT %s OFFSET %s
            """, (seller["seller_id"], per_page, offset_r))
            returns = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "seller_cs.html",
        seller=seller,
        questions=questions,
        returns=returns,
        page_q=page_q,
        page_r=page_r,
        total_pages_q=total_pages_q,
        total_pages_r=total_pages_r
    )


@app.route("/seller/cs/reply/<int:cs_id>", methods=["POST"])
def reply_cs(cs_id):
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    reply = request.form.get("reply", "").strip()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE customer_service
                SET cs_reply = %s,
                    cs_status = CASE
                        WHEN cs_status = '접수' THEN '처리중'
                        ELSE cs_status
                    END
                WHERE cs_id = %s
                  AND seller_id = %s
            """, (reply, cs_id, seller["seller_id"]))
            conn.commit()

        flash("답변이 등록되었습니다.")
    except Exception as e:
        conn.rollback()
        flash(f"답변 등록 중 오류: {e}")
    finally:
        conn.close()

    return redirect(url_for("seller_cs"))


@app.route("/seller/cs/status/<int:cs_id>", methods=["POST"])
def update_cs_status(cs_id):
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    cs_status = request.form.get("cs_status", "").strip()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE customer_service
                SET cs_status = %s
                WHERE cs_id = %s
                  AND seller_id = %s
            """, (cs_status, cs_id, seller["seller_id"]))
            conn.commit()

        flash("문의 상태가 변경되었습니다.")
    except Exception as e:
        conn.rollback()
        flash(f"문의 상태 변경 중 오류: {e}")
    finally:
        conn.close()

    return redirect(url_for("seller_cs"))


@app.route("/seller/cs/delete", methods=["POST"])
def delete_cs():
    ensure_seller_session()
    if not require_seller():
        return redirect(url_for("admin_login"))

    seller = get_current_seller()
    delete_ids = request.form.getlist("delete_ids")

    if not delete_ids:
        flash("삭제할 문의를 선택하세요.")
        return redirect(url_for("seller_cs"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(delete_ids))
            sql = f"""
                DELETE FROM customer_service
                WHERE seller_id = %s
                  AND cs_id IN ({placeholders})
            """
            cur.execute(sql, tuple([seller["seller_id"]] + delete_ids))
            conn.commit()

        flash("선택한 문의가 삭제되었습니다.")
    except Exception as e:
        conn.rollback()
        flash(f"문의 삭제 중 오류: {e}")
    finally:
        conn.close()

    return redirect(url_for("seller_cs"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)