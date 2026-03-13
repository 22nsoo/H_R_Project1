import os
import pickle
from io import BytesIO

import clip
import numpy as np
import requests
import torch
from PIL import Image

from db import get_connection

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)


def load_image_from_url(url: str):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def fetch_products():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    product_id,
                    product_name,
                    brand_name,
                    category1,
                    price,
                    size,
                    image_main1,
                    color
                FROM products
                WHERE image_main1 IS NOT NULL
                  AND image_main1 <> ''
                  AND status <> '숨김'
                ORDER BY product_id ASC
                """
            )
            return cursor.fetchall()
    finally:
        conn.close()


def make_embeddings():
    products = fetch_products()
    embeddings = []
    items = []

    for idx, product in enumerate(products, start=1):
        try:
            print(f"[{idx}/{len(products)}] {product['brand_name']} - {product['product_name']}")
            image = load_image_from_url(product["image_main1"])
            image_input = preprocess(image).unsqueeze(0).to(device)

            with torch.no_grad():
                image_feature = model.encode_image(image_input)
                image_feature /= image_feature.norm(dim=-1, keepdim=True)

            embeddings.append(image_feature.cpu().numpy()[0])
            items.append(
                {
                    "product_id": product["product_id"],
                    "name": product["product_name"],
                    "brand": product["brand_name"],
                    "category": product["category1"],
                    "price": product["price"],
                    "size_options": product["size"],
                    "img": product["image_main1"],
                    "color": product.get("color"),
                }
            )
        except Exception as e:
            print(f"실패: {product['product_name']} / {e}")

    if not embeddings:
        raise RuntimeError("임베딩 생성에 실패했습니다. 저장할 상품 이미지가 없습니다.")

    embeddings = np.array(embeddings, dtype=np.float32)

    with open("embeddings.pkl", "wb") as f:
        pickle.dump({"embeddings": embeddings, "items": items}, f)

    print(f"embeddings.pkl 생성 완료 / 총 {len(items)}개 상품")


if __name__ == "__main__":
    make_embeddings()