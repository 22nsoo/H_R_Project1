import os
import pickle
import requests
import numpy as np
import torch
import clip

from io import BytesIO
from PIL import Image

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

PRODUCT_CATALOG = [
    {
        "name": "에센셜 로고 티셔츠",
        "brand": "FILA",
        "img": "https://image.msscdn.net/thumbnails/images/goods_img/20200318/1356873/1356873_4_big.jpg?w=1200",
    },
    {
        "name": "993 클래식 그레이",
        "brand": "뉴발란스",
        "img": "https://img.soldout.co.kr/item_thumb/2023/09/14/f04ad920-2f97-4cfd-a8fb-1f9562f3a9d6.png/soldout/resize/1000/optimize",
    },
    {
        "name": "드라이핏 쇼츠",
        "brand": "나이키",
        "img": "https://image.msscdn.net/thumbnails/images/prd_img/20240603/4172781/detail_4172781_17183286905900_big.jpg?w=1200",
    },
    {
        "name": "T7 트랙 자켓",
        "brand": "푸마",
        "img": "https://image.msscdn.net/thumbnails/images/goods_img/20220720/2673600/2673600_2_big.jpg?w=1200",
    },
    {
        "name": "버클 로고 크롭탑",
        "brand": "마뗑킴",
        "img": "https://cafe24img.poxo.com/kimdaniyaya/web/product/medium/202305/37f18e1d5d4fc7735778f2097bf34a05.jpg",
    },
    {
        "name": "나일론 카고 팬츠",
        "brand": "마뗑킴",
        "img": "https://image.msscdn.net/thumbnails/images/prd_img/20260204/5982724/detail_5982724_17703421244670_big.jpg?w=1200",
    },
    {
        "name": "에어포스 1 '07",
        "brand": "나이키",
        "img": "https://image.msscdn.net/images/goods_img/20210202/1773099/1773099_1_500.jpg",
    },
    {
        "name": "스웨이드 클래식 XXI",
        "brand": "푸마",
        "img": "https://image.msscdn.net/images/goods_img/20210427/1922803/1922803_1_500.jpg",
    },
]


def load_image_from_url(url: str) -> Image.Image:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def make_embeddings():
    embeddings = []
    items = []

    for idx, product in enumerate(PRODUCT_CATALOG, start=1):
        try:
            print(f"[{idx}/{len(PRODUCT_CATALOG)}] 처리 중: {product['brand']} - {product['name']}")
            image = load_image_from_url(product["img"])
            image_input = preprocess(image).unsqueeze(0).to(device)

            with torch.no_grad():
                image_feature = model.encode_image(image_input)
                image_feature /= image_feature.norm(dim=-1, keepdim=True)

            embeddings.append(image_feature.cpu().numpy()[0])
            items.append({
                "name": product["name"],
                "brand": product["brand"],
                "img": product["img"],
            })

        except Exception as e:
            print(f"실패: {product['name']} / {e}")

    if not embeddings:
        raise RuntimeError("임베딩 생성에 실패했습니다. 저장할 데이터가 없습니다.")

    embeddings = np.array(embeddings, dtype=np.float32)

    data = {
        "embeddings": embeddings,
        "items": items,
    }

    with open("embeddings.pkl", "wb") as f:
        pickle.dump(data, f)

    print("\nembeddings.pkl 생성 완료")
    print(f"저장된 상품 수: {len(items)}")


if __name__ == "__main__":
    make_embeddings()