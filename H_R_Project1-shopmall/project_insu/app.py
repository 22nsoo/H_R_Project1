from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_connection, get_product_connection

app = Flask(__name__)
app.secret_key = "musinsa_secret_key"


def _merge_product_row(row):
    return {
        "id": row.get("product_id"),
        "name": row.get("product_name"),
        "price": row.get("price") or 0,
        "brand": row.get("brand") or "",
        "desc": row.get("description") or "",
        "category": row.get("category") or "",
        "img": row.get("image_url") or "",
        "size_options": row.get("size_options") or "",
        "stock": row.get("stock") or 0,
        "status": row.get("status") or "",
        "product_code": row.get("product_code") or "",
        "seller_id": row.get("seller_id"),
        "color": row.get("color") or "",
        "gender": row.get("gender") or "",
    }


def get_all_products():
    conn = get_product_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM products_for_shop
                ORDER BY product_id ASC
            """)
            rows = cursor.fetchall()
        return [_merge_product_row(row) for row in rows]
    finally:
        conn.close()


def get_product_by_id(product_id):
    conn = get_product_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM products_for_shop
                WHERE product_id = %s
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
    search_query = request.args.get("search", "").strip().lower()
    current_cate = request.args.get("cate", "ALL")
    user_name = session.get("user_name")

    items = get_all_products()
    display_items = items

    if request.method == "POST":
        file = request.files.get("search_img")

        if not file or file.filename == "":
            flash("이미지 파일을 선택해주세요.")
            return render_template(
                "main.html",
                items=items,
                user_name=user_name,
                current_cate=current_cate,
            )

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
            matched_products = match_products_from_image_results(image_results, items)

            if matched_products:
                display_items = matched_products
            else:
                display_items = []
                flash("유사한 상품을 찾지 못했습니다.")

        except Exception as e:
            flash(f"이미지 검색 중 오류가 발생했습니다: {e}")
            display_items = items

        return render_template(
            "main.html",
            items=display_items,
            user_name=user_name,
            current_cate="AI 이미지 검색 결과",
        )

    if search_query:
        display_items = [
            p for p in items
            if search_query in p["name"].lower() or search_query in p["brand"].lower()
        ]
        current_cate = f"'{search_query}' 검색 결과"
    elif current_cate != "ALL":
        display_items = [p for p in items if p["category"] == current_cate]

    return render_template(
        "main.html",
        items=display_items,
        user_name=user_name,
        current_cate=current_cate,
    )


@app.route("/product/<int:p_id>")
def product_detail(p_id):
    product = get_product_by_id(p_id)
    if not product:
        return "상품을 찾을 수 없습니다.", 404

    # 현재는 shoppingmall3 상품과 shoppingmall 리뷰 FK 구조가 분리되어 있어
    # 리뷰/추천 기능은 임시 비활성화
    reviews = []
    recommendation = None

    return render_template(
        "detail.html",
        p=product,
        product=product,
        reviews=reviews,
        recommendation=recommendation,
    )


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

    flash("현재 리뷰 기능은 상품 DB 연동 구조 조정 중입니다.")
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


@app.route("/order_complete")
def order_complete():
    session.pop("cart", None)
    return render_template("complete.html")


if __name__ == "__main__":
    app.run(debug=True)