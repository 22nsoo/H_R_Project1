from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_connection
from recommendation import get_size_recommendation

app = Flask(__name__)
app.secret_key = "fit-recommend-demo-secret"


@app.route("/")
def home():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products ORDER BY product_id ASC")
            products = cursor.fetchall()
        return render_template("home.html", products=products)
    finally:
        conn.close()


@app.route("/demo-login/<int:user_id>")
def demo_login(user_id):
    session["user_id"] = user_id
    flash(f"데모 로그인 완료: user_id={user_id}")
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃 되었습니다.")
    return redirect(url_for("home"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("먼저 로그인하세요.")
        return redirect(url_for("home"))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == "POST":
                gender = request.form.get("gender")
                height = request.form.get("height", type=int)
                weight = request.form.get("weight", type=int)
                preferred_fit = request.form.get("preferred_fit")
                usual_size = request.form.get("usual_size")

                cursor.execute(
                    """
                    UPDATE users
                    SET gender=%s, height=%s, weight=%s, preferred_fit=%s, usual_size=%s
                    WHERE user_id=%s
                    """,
                    (gender, height, weight, preferred_fit, usual_size, user_id),
                )
                conn.commit()
                flash("프로필이 저장되었습니다.")
                return redirect(url_for("profile"))

            cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            user = cursor.fetchone()
        return render_template("profile.html", user=user)
    finally:
        conn.close()


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_connection()
    user_id = session.get("user_id")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE product_id=%s", (product_id,))
            product = cursor.fetchone()
            if not product:
                flash("상품을 찾을 수 없습니다.")
                return redirect(url_for("home"))

            cursor.execute(
                """
                SELECT r.*, u.username, u.height, u.weight, u.preferred_fit
                FROM reviews r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.product_id=%s
                ORDER BY r.created_at DESC
                """,
                (product_id,),
            )
            reviews = cursor.fetchall()

        recommendation = None
        if user_id:
            recommendation = get_size_recommendation(user_id, product_id)

        return render_template(
            "product_detail.html",
            product=product,
            reviews=reviews,
            recommendation=recommendation,
        )
    finally:
        conn.close()


@app.route("/review/create/<int:product_id>", methods=["GET", "POST"])
def review_create(product_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("리뷰 작성을 위해 로그인하세요.")
        return redirect(url_for("home"))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE product_id=%s", (product_id,))
            product = cursor.fetchone()
            if not product:
                flash("상품을 찾을 수 없습니다.")
                return redirect(url_for("home"))

            if request.method == "POST":
                purchased_size = request.form.get("purchased_size")
                size_feel = request.form.get("size_feel")
                fit_feel = request.form.get("fit_feel")
                rating = request.form.get("rating", type=int)
                review_text = request.form.get("review_text", "").strip()

                cursor.execute(
                    """
                    INSERT INTO reviews (user_id, product_id, purchased_size, size_feel, fit_feel, rating, review_text)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, product_id, purchased_size, size_feel, fit_feel, rating, review_text),
                )
                conn.commit()
                flash("리뷰가 등록되었습니다.")
                return redirect(url_for("product_detail", product_id=product_id))

        return render_template("review_form.html", product=product)
    finally:
        conn.close()


@app.route("/init-demo")
def init_demo():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 기존 데모 데이터 초기화
            cursor.execute("DELETE FROM reviews")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM users")
            cursor.execute("ALTER TABLE reviews AUTO_INCREMENT = 1")
            cursor.execute("ALTER TABLE products AUTO_INCREMENT = 1")
            cursor.execute("ALTER TABLE users AUTO_INCREMENT = 1")

            # Demo users (1~14번 user_id 기준으로 맞춤)
            demo_users = [
                ("insu", "1234", "male", 173, 68, "세미오버핏", "M"),     # 1
                ("minho", "1234", "male", 172, 67, "세미오버핏", "M"),    # 2
                ("jinho", "1234", "male", 174, 70, "세미오버핏", "M"),    # 3
                ("sujin", "1234", "female", 160, 50, "정핏", "S"),        # 4
                ("hyun", "1234", "male", 173, 66, "세미오버핏", "M"),     # 5
                ("taeho", "1234", "male", 173, 68, "세미오버핏", "M"),    # 6
                ("jun", "1234", "male", 172, 65, "세미오버핏", "M"),      # 7
                ("woojin", "1234", "male", 176, 72, "오버핏", "L"),       # 8
                ("seong", "1234", "male", 170, 64, "정핏", "S"),          # 9
                ("yong", "1234", "male", 174, 68, "세미오버핏", "M"),     # 10
                ("dong", "1234", "male", 172, 67, "세미오버핏", "M"),     # 11
                ("jiwon", "1234", "female", 162, 52, "오버핏", "L"),      # 12
                ("hojun", "1234", "male", 178, 75, "오버핏", "L"),        # 13
                ("minseok", "1234", "male", 173, 69, "세미오버핏", "M"),  # 14
            ]
            for u in demo_users:
                cursor.execute(
                    """
                    INSERT INTO users (username, password, gender, height, weight, preferred_fit, usual_size)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    u,
                )

            # Demo products (1~3번 product_id 기준)
            demo_products = [
                ("오버핏 스트라이프 셔츠", "DemoBrand", "top", 49000, "S,M,L,XL"),  # 1
                ("와이드 데님 팬츠", "DemoBrand", "bottom", 59000, "S,M,L"),       # 2
                ("후드 집업", "DemoBrand", "outer", 69000, "M,L,XL"),              # 3
            ]
            for p in demo_products:
                cursor.execute(
                    """
                    INSERT INTO products (product_name, brand, category, price, size_options)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    p,
                )

            demo_reviews = [
                (2, 1, "M", "정사이즈", "세미오버핏", 5, "정사이즈 느낌이고 어깨가 편함. 세미오버핏으로 만족"),
                (3, 1, "M", "정사이즈", "세미오버핏", 4, "기장 무난하고 너무 크지 않아서 만족"),
                (5, 1, "L", "큼", "오버핏", 3, "L은 조금 큰 편. 오버핏 좋아하면 괜찮음"),

                (2, 2, "M", "정사이즈", "세미오버핏", 4, "허리 적당하고 핏이 자연스러움. M이 무난함"),
                (3, 2, "M", "정사이즈", "세미오버핏", 5, "173~174 정도면 M 추천. 기장도 적당함"),
                (4, 2, "L", "큼", "오버핏", 3, "와이드하게 입으려면 L도 괜찮지만 허리가 조금 큼"),

                (2, 3, "M", "정사이즈", "세미오버핏", 5, "어깨 편하고 가볍게 걸치기 좋음"),
                (3, 3, "M", "정사이즈", "세미오버핏", 4, "두께감 적당하고 세미오버핏 느낌 잘 남"),
                (5, 3, "L", "큼", "오버핏", 3, "오버하게 입으려면 괜찮지만 생각보다 살짝 큼"),

                (6, 1, "M", "정사이즈", "세미오버핏", 5, "173 기준 M이 제일 무난했고 재질도 괜찮음"),
                (7, 1, "M", "정사이즈", "세미오버핏", 4, "기장 적당하고 어깨 라인도 자연스러움"),
                (8, 1, "L", "큼", "오버핏", 4, "여유 있게 입으려면 L도 괜찮지만 M이 더 무난할 듯"),
                (9, 1, "S", "작음", "정핏", 2, "정핏 느낌이라 생각보다 작게 느껴졌음"),
                (10, 1, "M", "정사이즈", "세미오버핏", 5, "세미오버핏 좋아하면 M 추천. 너무 크지 않아서 좋음"),
                (11, 1, "M", "정사이즈", "세미오버핏", 4, "어깨 편하고 기장도 딱 적당했음"),
                (12, 1, "L", "정사이즈", "오버핏", 4, "오버핏 선호하면 L도 괜찮고 편하게 입기 좋음"),
                (13, 1, "M", "정사이즈", "세미오버핏", 5, "173~175 체형이면 M이 가장 안정적임"),
                (14, 1, "M", "정사이즈", "세미오버핏", 5, "전체적으로 만족. 재질도 좋고 핏도 예쁨"),

                (6, 2, "M", "정사이즈", "세미오버핏", 4, "허리 편하고 통도 과하지 않아서 좋음"),
                (7, 2, "M", "정사이즈", "세미오버핏", 5, "기장감 좋고 신발 위로 떨어지는 핏이 예쁨"),
                (8, 2, "L", "큼", "오버핏", 3, "오버하게 입기는 좋지만 허리는 좀 큰 편"),
                (10, 2, "M", "정사이즈", "세미오버핏", 5, "173 기준 M이 제일 자연스러웠음"),
                (11, 2, "M", "작음", "정핏", 3, "허리가 약간 타이트하게 느껴졌음"),
                (13, 2, "L", "정사이즈", "오버핏", 4, "통 넓게 입는 스타일이면 L도 괜찮음"),
                (14, 2, "M", "정사이즈", "세미오버핏", 4, "무난하게 코디하기 좋고 핏도 깔끔함"),

                (6, 3, "M", "정사이즈", "세미오버핏", 5, "후드 크기 적당하고 어깨가 편안함"),
                (7, 3, "M", "정사이즈", "세미오버핏", 4, "기장 적당하고 손이 자주 가는 핏"),
                (8, 3, "L", "큼", "오버핏", 3, "오버핏으로는 좋지만 생각보다 조금 큼"),
                (10, 3, "M", "정사이즈", "세미오버핏", 5, "173~174 체형이면 M이 가장 무난함"),
                (11, 3, "M", "정사이즈", "세미오버핏", 4, "두께감 적당하고 봄가을에 입기 좋음"),
                (13, 3, "L", "정사이즈", "오버핏", 4, "오버핏 선호하면 L 추천"),
                (14, 3, "M", "정사이즈", "세미오버핏", 5, "세미오버핏으로 깔끔하게 떨어져서 만족"),
            ]

            for r in demo_reviews:
                cursor.execute(
                    """
                    INSERT INTO reviews (
                        user_id, product_id, purchased_size, size_feel, fit_feel, rating, review_text
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    r,
                )

            conn.commit()

        flash("데모 데이터가 삽입되었습니다. /demo-login/1 로 로그인해 보세요.")
        return redirect(url_for("home"))
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
