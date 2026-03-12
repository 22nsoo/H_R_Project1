from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_connection
from recommendation import get_size_recommendation

app = Flask(__name__)
app.secret_key = "musinsa_secret_key"


PRODUCT_CATALOG = [
    {
        "name": "에센셜 로고 티셔츠",
        "price": 39000,
        "brand": "FILA",
        "desc": "휠라의 헤리티지가 담긴 로고 티셔츠입니다.",
        "category": "TOP",
        "img": "https://image.msscdn.net/thumbnails/images/goods_img/20200318/1356873/1356873_4_big.jpg?w=1200",
        "size_options": "S,M,L,XL",
    },
    {
        "name": "993 클래식 그레이",
        "price": 259000,
        "brand": "뉴발란스",
        "desc": "클래식의 정점, 993 스니커즈입니다.",
        "category": "SHOES",
        "img": "https://img.soldout.co.kr/item_thumb/2023/09/14/f04ad920-2f97-4cfd-a8fb-1f9562f3a9d6.png/soldout/resize/1000/optimize",
        "size_options": "250,260,270,280",
    },
    {
        "name": "드라이핏 쇼츠",
        "price": 45000,
        "brand": "나이키",
        "desc": "기능성 트레이닝 반바지입니다.",
        "category": "PANTS",
        "img": "https://image.msscdn.net/thumbnails/images/prd_img/20240603/4172781/detail_4172781_17183286905900_big.jpg?w=1200",
        "size_options": "S,M,L,XL",
    },
    {
        "name": "T7 트랙 자켓",
        "price": 89000,
        "brand": "푸마",
        "desc": "푸마의 상징적인 트랙 자켓입니다.",
        "category": "OUTER",
        "img": "https://image.msscdn.net/thumbnails/images/goods_img/20220720/2673600/2673600_2_big.jpg?w=1200",
        "size_options": "S,M,L,XL",
    },
    {
        "name": "버클 로고 크롭탑",
        "price": 68000,
        "brand": "마뗑킴",
        "desc": "시크한 감성의 상의입니다.",
        "category": "TOP",
        "img": "https://cafe24img.poxo.com/kimdaniyaya/web/product/medium/202305/37f18e1d5d4fc7735778f2097bf34a05.jpg",
        "size_options": "S,M,L",
    },
    {
        "name": "나일론 카고 팬츠",
        "price": 128000,
        "brand": "마뗑킴",
        "desc": "힙한 실루엣의 팬츠입니다.",
        "category": "PANTS",
        "img": "https://image.msscdn.net/thumbnails/images/prd_img/20260204/5982724/detail_5982724_17703421244670_big.jpg?w=1200",
        "size_options": "S,M,L",
    },
    {
        "name": "에어포스 1 '07",
        "price": 139000,
        "brand": "나이키",
        "desc": "모두의 머스트 해브 아이템, 에어포스입니다.",
        "category": "SHOES",
        "img": "https://image.msscdn.net/images/goods_img/20210202/1773099/1773099_1_500.jpg",
        "size_options": "250,260,270,280",
    },
    {
        "name": "스웨이드 클래식 XXI",
        "price": 99000,
        "brand": "푸마",
        "desc": "푸마의 영원한 아이콘 스웨이드 스니커즈입니다.",
        "category": "SHOES",
        "img": "https://image.msscdn.net/images/goods_img/20210427/1922803/1922803_1_500.jpg",
        "size_options": "250,260,270,280",
    },
]


def _catalog_key(name, brand):
    return f"{name}__{brand}"


CATALOG_MAP = {
    _catalog_key(item["name"], item["brand"]): item
    for item in PRODUCT_CATALOG
}


def seed_products_if_needed():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for item in PRODUCT_CATALOG:
                cursor.execute(
                    """
                    SELECT product_id
                    FROM products
                    WHERE product_name=%s AND brand=%s
                    """,
                    (item["name"], item["brand"]),
                )
                found = cursor.fetchone()
                if not found:
                    cursor.execute(
                        """
                        INSERT INTO products (product_name, brand, category, price, size_options)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            item["name"],
                            item["brand"],
                            item["category"],
                            item["price"],
                            item["size_options"],
                        ),
                    )
            conn.commit()
    finally:
        conn.close()


def _merge_product_row(row):
    key = _catalog_key(row.get("product_name", ""), row.get("brand", ""))
    meta = CATALOG_MAP.get(key, {})

    return {
        "id": row.get("product_id"),
        "name": row.get("product_name"),
        "price": row.get("price") or 0,
        "brand": row.get("brand") or "",
        "desc": meta.get("desc", row.get("size_options", "")),
        "category": row.get("category") or meta.get("category", ""),
        "img": meta.get("img", ""),
        "size_options": row.get("size_options", ""),
    }


def get_all_products():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products ORDER BY product_id ASC")
            rows = cursor.fetchall()
        return [_merge_product_row(row) for row in rows]
    finally:
        conn.close()


def get_product_by_id(product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE product_id=%s", (product_id,))
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


@app.before_request
def ensure_seed_data():
    seed_products_if_needed()


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

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.*, u.username, u.height, u.weight, u.preferred_fit
                FROM reviews r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.product_id=%s
                ORDER BY r.created_at DESC
                """,
                (p_id,),
            )
            reviews = cursor.fetchall()
    finally:
        conn.close()

    recommendation = None
    user_id = session.get("user_id")
    if user_id:
        try:
            recommendation = get_size_recommendation(user_id, p_id)
        except Exception:
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
            cursor.execute("TRUNCATE TABLE products")
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

            demo_products = [
                ("에센셜 로고 티셔츠", "FILA", "TOP", 39000, "S,M,L,XL"),
                ("993 클래식 그레이", "뉴발란스", "SHOES", 259000, "250,260,270,280"),
                ("드라이핏 쇼츠", "나이키", "PANTS", 45000, "S,M,L,XL"),
                ("T7 트랙 자켓", "푸마", "OUTER", 89000, "S,M,L,XL"),
                ("버클 로고 크롭탑", "마뗑킴", "TOP", 68000, "S,M,L"),
                ("나일론 카고 팬츠", "마뗑킴", "PANTS", 128000, "S,M,L"),
                ("에어포스 1 '07", "나이키", "SHOES", 139000, "250,260,270,280"),
                ("스웨이드 클래식 XXI", "푸마", "SHOES", 99000, "250,260,270,280"),
            ]

            for p in demo_products:
                cursor.execute(
                    """
                    INSERT INTO products
                    (product_name, brand, category, price, size_options)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    p,
                )

            demo_reviews = [
                (2, 1, "M", "정사이즈", "세미오버핏", 5, "정사이즈 느낌이고 어깨가 편함. 세미오버핏으로 만족"),
                (3, 1, "M", "정사이즈", "세미오버핏", 4, "기장 무난하고 너무 크지 않아서 만족"),
                (4, 1, "M", "정사이즈", "세미오버핏", 5, "173 전후 체형이면 M이 가장 무난한 느낌"),
                (5, 1, "L", "큼", "오버핏", 3, "L은 조금 큰 편. 오버핏 좋아하면 괜찮음"),
                (6, 1, "M", "정사이즈", "세미오버핏", 5, "재질도 괜찮고 핏도 깔끔함"),
                (9, 1, "M", "정사이즈", "세미오버핏", 4, "어깨가 편하고 전체적으로 무난함"),
                (10, 1, "M", "정사이즈", "세미오버핏", 5, "세미오버핏 좋아하면 M 추천"),
                (13, 1, "M", "정사이즈", "세미오버핏", 5, "173~175 체형이면 M이 안정적"),

                (2, 2, "270", "정사이즈", "정핏", 5, "발볼 무난하고 270이 가장 편했음"),
                (3, 2, "270", "정사이즈", "정핏", 4, "평소 270 신으면 무난하게 잘 맞음"),
                (4, 2, "280", "큼", "오버핏", 3, "한 치수 올리면 살짝 큼"),
                (10, 2, "270", "정사이즈", "정핏", 5, "착화감 좋고 사이즈도 잘 맞음"),
                (13, 2, "280", "정사이즈", "오버핏", 4, "여유 있게 신으려면 반업도 괜찮음"),

                (2, 3, "M", "정사이즈", "세미오버핏", 4, "허리 적당하고 활동하기 편함"),
                (3, 3, "M", "정사이즈", "세미오버핏", 5, "173~174 정도면 M 추천"),
                (5, 3, "L", "큼", "오버핏", 3, "L은 조금 큰 편"),
                (6, 3, "M", "정사이즈", "세미오버핏", 4, "운동할 때 입기 좋음"),
                (10, 3, "M", "정사이즈", "세미오버핏", 5, "길이감도 적당하고 편함"),

                (2, 4, "M", "정사이즈", "세미오버핏", 5, "어깨 편하고 세미오버핏 느낌 잘 남"),
                (3, 4, "M", "정사이즈", "세미오버핏", 4, "기장 적당하고 핏 깔끔함"),
                (5, 4, "L", "큼", "오버핏", 3, "오버하게 입을 거면 L도 괜찮음"),
                (10, 4, "M", "정사이즈", "세미오버핏", 5, "봄가을에 입기 좋음"),

                (11, 5, "S", "정사이즈", "정핏", 5, "크롭 기장감 예쁘고 핏 깔끔함"),
                (12, 5, "M", "정사이즈", "오버핏", 4, "조금 여유 있게 입으려면 M도 괜찮음"),

                (11, 6, "M", "정사이즈", "정핏", 4, "통이 예쁘고 길이감도 무난함"),
                (12, 6, "L", "정사이즈", "오버핏", 5, "오버핏 좋아하면 L 추천"),

                (2, 7, "270", "정사이즈", "정핏", 5, "평소 사이즈 그대로 가면 무난함"),
                (3, 7, "270", "정사이즈", "정핏", 4, "착화감 좋고 어디에나 잘 어울림"),

                (2, 8, "270", "정사이즈", "정핏", 4, "발볼 무난하고 디자인 괜찮음"),
                (3, 8, "270", "정사이즈", "정핏", 4, "사이즈는 정사이즈 추천"),
            ]

            for r in demo_reviews:
                cursor.execute(
                    """
                    INSERT INTO reviews
                    (user_id, product_id, purchased_size, size_feel, fit_feel, rating, review_text)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    r,
                )

            conn.commit()

        flash("데모 데이터 삽입 완료!")
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

    if request.method == "POST":
        purchased_size = request.form.get("purchased_size")
        size_feel = request.form.get("size_feel")
        fit_feel = request.form.get("fit_feel")
        rating = request.form.get("rating", type=int)
        review_text = request.form.get("review_text", "").strip()

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO reviews
                    (user_id, product_id, purchased_size, size_feel, fit_feel, rating, review_text)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        product_id,
                        purchased_size,
                        size_feel,
                        fit_feel,
                        rating,
                        review_text,
                    ),
                )
                conn.commit()
        finally:
            conn.close()

        flash("리뷰가 등록되었습니다.")
        return redirect(url_for("product_detail", p_id=product_id))

    return render_template(
        "review_form.html",
        product=product,
        p=product,
    )


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

@app.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # 1. 유저 정보 가져오기
        cur.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
        user_data = cur.fetchone()
        
        # 2. 장바구니 데이터 가져오기 (세션 활용)
        # main.html에서 session.get('cart')를 사용하므로 동일하게 가져옵니다.
        cart_data = session.get('cart', {})
        
        # 3. (선택사항) 결제 완료 내역이 있다면 여기서 추가로 SELECT 쿼리 실행
        # cur.execute("SELECT ... FROM orders WHERE user_id = %s", (session['user_id'],))
        # orders = cur.fetchall()
        
    except Exception as e:
        print(f"마이페이지 로딩 에러: {e}")
        cart_data = {}
    finally:
        cur.close()
        conn.close()
        
    # 중요: templates로 넘길 때 cart=cart_data를 꼭 넣어줍니다.
    return render_template('mypage.html', user=user_data, cart=cart_data)
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_connection()
    cur = conn.cursor()
    
    # POST: 수정한 내용을 DB에 저장
    if request.method == 'POST':
        gender = request.form.get('gender')
        height = request.form.get('height')
        weight = request.form.get('weight')
        preferred_fit = request.form.get('preferred_fit')
        usual_size = request.form.get('usual_size')
        
        try:
            cur.execute("""
                UPDATE users 
                SET gender=%s, height=%s, weight=%s, preferred_fit=%s, usual_size=%s 
                WHERE user_id=%s
            """, (gender, height, weight, preferred_fit, usual_size, session['user_id']))
            conn.commit()
            flash("정보가 성공적으로 수정되었습니다.")
            return redirect(url_for('mypage'))
        except Exception as e:
            print(f"수정 오류: {e}")
            flash("수정 중 오류가 발생했습니다.")
        finally:
            cur.close()
            conn.close()
            
    # GET: 기존 정보를 가져와서 수정 페이지에 보여줌
    else:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('edit_profile.html', user=user_data)

if __name__ == "__main__":
    app.run(debug=True)