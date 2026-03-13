from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_connection
import time
import os

app = Flask(__name__)
app.secret_key = "musinsa_secret_key"


def _merge_product_row(row):
    return {
        "id": row.get("product_id"),
        "name": row.get("product_name"),
        "price": row.get("price") or 0,
        "brand": row.get("brand_name") or "",
        "desc": row.get("description") or "",
        "category": row.get("category1") or "",
        "img": row.get("image_main1") or "",
        "size_options": row.get("size") or "",
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
                WHERE product_id = %s AND status <> '숨김'
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
            from werkzeug.utils import secure_filename

            upload_dir = os.path.join("static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            filename = secure_filename(file.filename)
            save_path = os.path.join(upload_dir, filename)
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
                "price": int(row.get("price") or 0),
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
                rev = {
                    "username": r.get("username"),
                    "created_at": r.get("created_at").strftime("%Y-%m-%d") if r.get("created_at") else "",
                    "purchased_size": r.get("purchased_size"),
                    "rating": r.get("rating"),
                    "size_feel": r.get("size_feel"),
                    "height": r.get("height"),
                    "weight": r.get("weight"),
                    "review_text": r.get("review_text"),
                }
                reviews.append(rev)

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
                "price": int(product["price"]),
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
                "price": int(item.get("price", 0)),
                "qty": int(item.get("qty", 1)),
                "seller_id": product.get("seller_id"),
                "selected_size": selected_size,
                "selected_color": selected_color,
            })

    receiver = request.form.get("receiver", "").strip()
    phone = request.form.get("phone", "").strip()
    address1 = request.form.get("address1", "").strip()
    address2 = request.form.get("address2", "").strip()
    address = f"{address1} {address2}".strip()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for item in items_to_order:
                order_code = f"ORD-{user_id}-{int(time.time())}-{item['p_id']}"
                total_amount = int(item["price"]) * int(item["qty"])

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
                SELECT o.order_date,
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
# ... (기존 상단 import 및 유틸리티 함수 유지)

# [추가된 CS 기능 1] 문의/교환/반품 작성
@app.route("/cs/create", methods=["GET", "POST"])
def cs_create():
    # ... (로그인 체크 생략)
    if request.method == "GET":
        o_id = request.args.get("order_id")
        p_id = request.args.get("product_id")
        
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # [핵심] image_main1을 반드시 'img'라는 이름으로 가져와야 HTML의 {{ product.img }}와 연결됩니다.
                sql = """
                    SELECT product_id, product_name, seller_id, image_main1 AS img 
                    FROM products 
                    WHERE product_id=%s
                """
                cur.execute(sql, (p_id,))
                product = cur.fetchone()
                
                # 만약 DB 연결 설정이 DictCursor가 아니라서 product['img'] 접근이 안 된다면
                # 아래처럼 딕셔너리로 강제 변환해서 넘겨주는 것이 안전합니다.
                if product and not isinstance(product, dict):
                    product = {
                        'product_id': product[0],
                        'product_name': product[1],
                        'seller_id': product[2],
                        'img': product[3]
                    }
        finally: conn.close()
        return render_template("cs_form.html", o_id=o_id, p_id=p_id, product=product)

    if request.method == "POST":
        o_id = request.form.get("order_id")
        p_id = request.form.get("product_id")
        s_id = request.form.get("seller_id")
        cs_type = request.form.get("cs_type")
        title = request.form.get("cs_title")
        content = request.form.get("cs_content")
        
        # order_id가 없으면(구매 전 문의) None(NULL)으로 처리
        final_o_id = int(o_id) if o_id and o_id != 'None' and o_id != '0' else None

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO customer_service (order_id, product_id, seller_id, customer_name, cs_type, cs_title, cs_content)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(sql, (final_o_id, p_id, s_id, session.get("user_name"), cs_type, title, content))
                conn.commit()
        finally: conn.close()
        return redirect(url_for("cs_list"))

# [추가된 CS 기능 2] 내 문의 내역 목록
@app.route("/cs/list")
def cs_list():
    user_id = session.get("user_id")
    if not user_id: return redirect(url_for("login"))
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
    finally: conn.close()
    return render_template("cs_list.html", cs_items=cs_items)

# [추가된 CS 기능 3] 문의 상세 보기
@app.route("/cs/detail/<int:cs_id>")
def cs_detail(cs_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cs.*, p.product_name 
                FROM customer_service cs 
                JOIN products p ON cs.product_id = p.product_id 
                WHERE cs_id=%s
            """, (cs_id,))
            cs_data = cur.fetchone()
    finally: conn.close()
    return render_template("cs_detail.html", cs=cs_data)

# ... (나머지 기존 라우트들 - mypage, product_detail 등 모두 유지)

if __name__ == "__main__":
    app.run(debug=True, port=5001)