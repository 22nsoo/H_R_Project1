from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_connection
import time

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


def match_products_from_image_results(image_results, items):
    matched = []

    for result in image_results:
        for item in items:
            if item["name"] == result["name"] and item["brand"] == result["brand"]:
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
    # 1. 파라미터 가져오기
    search_query = request.args.get("search", "").strip().lower()
    current_cate = request.args.get("cate", "ALL")
    user_name = session.get("user_name")

    # 2. 전체 상품 로드
    items = get_all_products()
    display_items = items

    # [핵심 수정] HTML의 영어 카테고리 값을 DB에 있는 한글 값으로 매핑합니다.
    category_map = {
        "TOP": "상의",
        "PANTS": "하의",
        "OUTER": "아우터",
        "SHOES": "신발"
    }

    # 3. AI 이미지 검색 처리 (POST 방식)
    if request.method == "POST":
        file = request.files.get("search_img")
        if file and file.filename != "":
            import os
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
                return render_template("main.html", items=display_items, user_name=user_name, current_cate="AI 이미지 검색 결과")
            except Exception as e:
                flash(f"이미지 검색 중 오류: {e}")

    # 4. 카테고리 필터링 (한글 매핑 적용)
    if current_cate != "ALL":
        # HTML에서 'TOP'이 넘어오면 '상의'로 바꿔서 DB 값과 비교합니다.
        target_db_value = category_map.get(current_cate, current_cate)
        
        display_items = [
            p for p in items 
            if str(p.get("category")).strip() == target_db_value
        ]

    # 5. 텍스트 검색 처리
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
    # DictCursor를 사용하여 p['price'] 처럼 키값으로 접근 (KeyError 방지)
    cur = conn.cursor(dictionary=True) if hasattr(conn, 'cursor') and 'dictionary' in str(conn.cursor) else conn.cursor()
    
    try:
        # 1. 상품 정보 조회 (html의 p. 변수들과 이름 일치시킴)
        product_sql = """
            SELECT 
                product_id AS id, product_name AS name, price, description AS `desc`, 
                brand_name AS brand, image_main1 AS img, size AS size_options 
            FROM products 
            WHERE product_id = %s
        """
        cur.execute(product_sql, (p_id,))
        # dictionary=True가 안될 경우를 대비해 fetchone 결과 처리
        row = cur.fetchone()
        
        if not row:
            return "<script>alert('상품을 찾을 수 없습니다.'); history.back();</script>"

        # 데이터 매핑 (튜플일 경우와 딕셔너리일 경우 모두 대응)
        if isinstance(row, dict):
            product = row
        else:
            product = {
                'id': row[0], 'name': row[1], 'price': row[2], 'desc': row[3],
                'brand': row[4], 'img': row[5], 'size_options': row[6]
            }
        
        # 가격 숫자 변환 (TypeError 방지)
        product['price'] = int(product['price']) if product['price'] else 0

        # 2. 리뷰 데이터 조회 (u.username, u.height 등 detail.html의 review. 변수와 일치)
        review_sql = """
            SELECT 
                u.username, r.created_at, r.purchased_size, r.rating, 
                r.size_feel, u.height, u.weight, r.review_text
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.product_id = %s
            ORDER BY r.created_at DESC
        """
        cur.execute(review_sql, (p_id,))
        review_rows = cur.fetchall()
        
        reviews = []
        for r in review_rows:
            if isinstance(r, dict):
                rev = r
            else:
                rev = {
                    'username': r[0], 'created_at': r[1], 'purchased_size': r[2],
                    'rating': r[3], 'size_feel': r[4], 'height': r[5], 'weight': r[6], 'review_text': r[7]
                }
            
            if rev['created_at']:
                rev['created_at'] = rev['created_at'].strftime('%Y-%m-%d')
            reviews.append(rev)

        # 3. 사이즈 추천 (로그인 세션 기반)
        recommendation = None
        user_id = session.get('user_id')
        if user_id:
            cur.execute("SELECT height, weight FROM users WHERE user_id = %s", (user_id,))
            u_info = cur.fetchone()
            # u_info 처리
            u_h = u_info['height'] if isinstance(u_info, dict) else u_info[0] if u_info else None
            u_w = u_info['weight'] if isinstance(u_info, dict) else u_info[1] if u_info else None
            
            if u_h and u_w:
                rec_sql = """
                    SELECT r.purchased_size, COUNT(*) as cnt
                    FROM reviews r JOIN users u ON r.user_id = u.user_id
                    WHERE r.product_id = %s AND u.height BETWEEN %s-3 AND %s+3 AND u.weight BETWEEN %s-3 AND %s+3
                    GROUP BY r.purchased_size ORDER BY cnt DESC LIMIT 1
                """
                cur.execute(rec_sql, (p_id, u_h, u_h, u_w, u_w))
                rec_row = cur.fetchone()
                if rec_row:
                    recommendation = {
                        'recommended_size': rec_row['purchased_size'] if isinstance(rec_row, dict) else rec_row[0],
                        'message': "고객님과 비슷한 체형의 사용자들이 가장 많이 선택한 사이즈입니다.",
                        'match_count': rec_row['cnt'] if isinstance(rec_row, dict) else rec_row[1]
                    }

    except Exception as e:
        print(f"Error detail: {e}")
    finally:
        cur.close()
        conn.close()

    return render_template("detail.html", p=product, reviews=reviews, recommendation=recommendation)


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

    if request.method == "GET":
        return render_template("review_form.html", product=product)

    if request.method == "POST":
        # 1. 폼 데이터 가져오기 (HTML의 name 속성과 일치해야 함)
        purchased_size = request.form.get("purchased_size")
        size_feel = request.form.get("size_feel")
        fit_feel = request.form.get("fit_feel")
        rating = request.form.get("rating")
        review_text = request.form.get("review_text")

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # [수정 완료] DB 설계문(reviews 테이블)과 컬럼명을 완벽히 맞췄습니다.
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

        # 등록 후 상품 상세 페이지로 이동 (p_id 파라미터 확인)
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
            }

        session["cart"] = cart
        session.modified = True

    if action == "buy":
        return redirect(url_for("order_page"))

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


@app.route("/order_complete", methods=["GET", "POST"])
def order_complete():
    user_id = session.get("user_id")
    cart = session.get("cart", {})

    if user_id and cart:
        receiver = request.values.get("receiver", "")
        phone = request.values.get("phone", "")
        address1 = request.values.get("address1", "")
        address2 = request.values.get("address2", "")
        address = f"{address1} {address2}".strip()

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                for p_id_str, item in cart.items():
                    product = get_product_by_id(int(p_id_str))
                    seller_id = product["seller_id"] if product else None

                    cursor.execute(
                        """
                        INSERT INTO orders
                        (order_code, seller_id, user_id, customer_name,
                        customer_phone, address, total_amount, order_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, '신규주문')
                        """,
                        (
                            f"ORD-{user_id}-{p_id_str}-{int(time.time())}",
                            seller_id,
                            user_id,
                            receiver,
                            phone,
                            address,
                            item.get("price", 0) * item.get("qty", 1),
                        ),
                    )
                    order_id = cursor.lastrowid

                    cursor.execute(
                        """
                        INSERT INTO order_items
                        (order_id, product_id, quantity, unit_price, subtotal)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            int(p_id_str),
                            item.get("qty", 1),
                            item.get("price", 0),
                            item.get("price", 0) * item.get("qty", 1),
                        ),
                    )

                conn.commit()
        finally:
            conn.close()

    session.pop("cart", None)
    return render_template("complete.html")


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
                SELECT o.order_date, p.product_name AS name,
                    oi.subtotal AS price, o.order_status AS status
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


if __name__ == "__main__":
    app.run(debug=True)