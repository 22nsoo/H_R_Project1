from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "musinsa_secret_key"

USERS = {"test": {"pw": "1234", "name": "김무신"}}

PRODUCTS = [
    {"id": 1, "name": "에센셜 로고 티셔츠", "price": 39000, "brand": "FILA", "desc": "휠라의 헤리티지가 담긴 로고 티셔츠입니다.", "category": "TOP", 
    "img": "https://image.msscdn.net/thumbnails/images/goods_img/20200318/1356873/1356873_4_big.jpg?w=1200"},
    {"id": 2, "name": "993 클래식 그레이", "price": 259000, "brand": "뉴발란스", "desc": "클래식의 정점, 993 스니커즈입니다.", "category": "SHOES", 
    "img": "https://img.soldout.co.kr/item_thumb/2023/09/14/f04ad920-2f97-4cfd-a8fb-1f9562f3a9d6.png/soldout/resize/1000/optimize"},
    {"id": 3, "name": "드라이핏 쇼츠", "price": 45000, "brand": "나이키", "desc": "기능성 트레이닝 반바지입니다.", "category": "PANTS", 
    "img": "https://image.msscdn.net/thumbnails/images/prd_img/20240603/4172781/detail_4172781_17183286905900_big.jpg?w=1200"},
    {"id": 4, "name": "T7 트랙 자켓", "price": 89000, "brand": "푸마", "desc": "푸마의 상징적인 트랙 자켓입니다.", "category": "OUTER", 
    "img": "https://image.msscdn.net/thumbnails/images/goods_img/20220720/2673600/2673600_2_big.jpg?w=1200"},
    {"id": 5, "name": "버클 로고 크롭탑", "price": 68000, "brand": "마뗑킴", "desc": "시크한 감성의 상의입니다.", "category": "TOP", 
    "img": "https://cafe24img.poxo.com/kimdaniyaya/web/product/medium/202305/37f18e1d5d4fc7735778f2097bf34a05.jpg"},
    {"id": 6, "name": "나일론 카고 팬츠", "price": 128000, "brand": "마뗑킴", "desc": "힙한 실루엣의 팬츠입니다.", "category": "PANTS", 
    "img": "https://image.msscdn.net/thumbnails/images/prd_img/20260204/5982724/detail_5982724_17703421244670_big.jpg?w=1200"},
    {"id": 7, "name": "에어포스 1 '07", "price": 139000, "brand": "나이키", "desc": "모두의 머스트 해브 아이템, 에어포스입니다.", "category": "SHOES", 
    "img": "https://image.msscdn.net/images/goods_img/20210202/1773099/1773099_1_500.jpg"},
    {"id": 8, "name": "스웨이드 클래식 XXI", "price": 99000, "brand": "푸마", "desc": "푸마의 영원한 아이콘 스웨이드 스니커즈입니다.", "category": "SHOES", 
    "img": "https://image.msscdn.net/images/goods_img/20210427/1922803/1922803_1_500.jpg"},
]

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    uid = request.form.get("uid")
    upw = request.form.get("upw")
    if uid in USERS and USERS[uid]["pw"] == upw:
        session["user_name"] = USERS[uid]["name"]
        return redirect(url_for("main_page"))
    else:
        flash("아이디 또는 비밀번호가 틀렸습니다.")
        return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main_page"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        user_pw = request.form.get("user_pw")
        user_name = request.form.get("user_name")
        gender = request.form.get("gender")
        height = request.form.get("height")
        weight = request.form.get("weight")
        size = request.form.get("size")
        USERS[user_id] = {"pw": user_pw, "name": user_name, "gender": gender, "height": height, "weight": weight, "size": size}
        return "<script>alert('회원가입 완료!'); location.href='/login';</script>"
    return render_template("signup.html")

@app.route("/main", methods=["GET", "POST"])
def main_page():
    search_query = request.args.get('search', '').strip().lower()
    current_cate = request.args.get('cate', 'ALL')
    user_name = session.get("user_name")
    display_items = PRODUCTS

    if request.method == "POST":
        file = request.files.get('search_img')
        if file and file.filename != '':
            filename = file.filename.lower()
            if "나이키" in filename or "nike" in filename:
                display_items = [p for p in PRODUCTS if p['brand'] == "나이키"]
            elif "푸마" in filename or "puma" in filename:
                display_items = [p for p in PRODUCTS if p['brand'] == "푸마"]
            elif "마뗑킴" in filename or "matin" in filename:
                display_items = [p for p in PRODUCTS if p['brand'] == "마뗑킴"]
            else:
                display_items = [p for p in PRODUCTS if p['brand'] == "나이키"]
            return render_template("main.html", items=display_items, user_name=user_name, current_cate="AI 이미지 검색 결과")

    if search_query:
        display_items = [p for p in PRODUCTS if search_query in p['name'].lower() or search_query in p['brand'].lower()]
        current_cate = f"'{search_query}' 검색 결과"
    elif current_cate != "ALL":
        display_items = [p for p in PRODUCTS if p['category'] == current_cate]

    return render_template("main.html", items=display_items, user_name=user_name, current_cate=current_cate)

@app.route("/product/<int:p_id>")
def product_detail(p_id):
    product = next((p for p in PRODUCTS if p['id'] == p_id), None)
    if not product:
        return "상품을 찾을 수 없습니다.", 404
    return render_template("detail.html", p=product)

@app.route("/add_cart/<int:p_id>")
def add_cart(p_id):
    action = request.args.get('action') # 'buy' 인지 확인
    product = next((p for p in PRODUCTS if p['id'] == p_id), None)
    if product:
        cart = session.get("cart", {})
        p_id_str = str(p_id)
        if p_id_str in cart:
            cart[p_id_str]['qty'] += 1
        else:
            cart[p_id_str] = {"name": product['name'], "price": product['price'], "brand": product['brand'], "img": product.get('img', ''), "qty": 1}
        session["cart"] = cart
        session.modified = True
    
    if action == 'buy':
        return redirect(url_for('order_page'))
    return redirect(url_for('cart_page'))

@app.route("/update_cart/<int:p_id>/<string:action>")
def update_cart(p_id, action):
    cart = session.get("cart", {})
    p_id_str = str(p_id)
    if p_id_str in cart:
        if action == 'plus':
            cart[p_id_str]['qty'] += 1
        elif action == 'minus':
            cart[p_id_str]['qty'] -= 1
            if cart[p_id_str]['qty'] <= 0:
                cart.pop(p_id_str)
        elif action == 'delete':
            cart.pop(p_id_str)
        session["cart"] = cart
        session.modified = True
    return redirect(url_for('cart_page'))

@app.route("/cart")
def cart_page():
    cart_dict = session.get("cart", {})
    cart_items = []
    total_price = 0
    for key, item in cart_dict.items():
        item['id'] = key # 수량 조절 버튼을 위해 ID 저장
        cart_items.append(item)
        total_price += item['price'] * item['qty']
    return render_template("cart.html", items=cart_items, total=total_price)

# 1. 주문/결제 관련 라우트 통합
@app.route("/order")
@app.route("/order/<int:p_id>")
def order_page(p_id=None):
    # 케이스 A: 상세페이지에서 '바로 구매하기'를 누른 경우 (p_id가 있음)
    if p_id is not None:
        product = next((p for p in PRODUCTS if p['id'] == p_id), None)
        if product:
            return render_template("order.html", p=product)
        return "상품을 찾을 수 없습니다.", 404
    
    # 케이스 B: 장바구니에서 '주문하기'를 누른 경우 (p_id가 없음)
    else:
        cart = session.get("cart")
        if not cart:
            flash("장바구니가 비어있습니다.")
            return redirect(url_for("main_page"))
        # 장바구니 전체 결제 로직이 필요하다면 여기에 추가 (현재는 order.html로 이동)
        return render_template("order.html")

# 2. 결제 완료 라우트 통합
@app.route("/order_complete")
def order_complete():
    # 결제가 끝났으니 장바구니를 비워줌
    session.pop("cart", None) 
    return render_template("complete.html")

if __name__ == "__main__":
    app.run(debug=True)