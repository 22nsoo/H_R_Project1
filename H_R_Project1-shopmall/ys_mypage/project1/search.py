import os
import pickle
from typing import List, Dict

import numpy as np
from PIL import Image
import torch
import clip

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBEDDINGS_PATH = os.path.join(BASE_DIR, "embeddings.pkl")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_MB = 5
MIN_IMAGE_SIDE = 160
MIN_SCORE = 0.22

_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = None
_preprocess = None
_cached_data = None


def _load_model():
    global _model, _preprocess
    if _model is None or _preprocess is None:
        _model, _preprocess = clip.load("ViT-B/32", device=_device)
    return _model, _preprocess


def _load_embeddings():
    global _cached_data
    if _cached_data is None:
        if not os.path.exists(EMBEDDINGS_PATH):
            raise FileNotFoundError(
                "embeddings.pkl 파일이 없습니다. 먼저 make_pkl.py를 실행해 임베딩을 생성하세요."
            )
        with open(EMBEDDINGS_PATH, "rb") as f:
            _cached_data = pickle.load(f)
    return _cached_data


def validate_query_image(image_path: str) -> None:
    if not os.path.exists(image_path):
        raise FileNotFoundError("업로드된 이미지 파일을 찾을 수 없습니다.")

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("지원 형식은 JPG, JPEG, PNG, WEBP 입니다.")

    file_size = os.path.getsize(image_path)
    if file_size > MAX_IMAGE_MB * 1024 * 1024:
        raise ValueError(f"이미지 용량은 {MAX_IMAGE_MB}MB 이하만 가능합니다.")

    with Image.open(image_path) as img:
        width, height = img.size
        if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
            raise ValueError(
                f"이미지 해상도는 최소 {MIN_IMAGE_SIDE}x{MIN_IMAGE_SIDE} 이상이어야 합니다."
            )


def get_image_requirements() -> Dict[str, object]:
    return {
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "max_size_mb": MAX_IMAGE_MB,
        "min_resolution": f"{MIN_IMAGE_SIDE}x{MIN_IMAGE_SIDE}",
        "guide": "상품이 중앙에 잘 보이고 배경이 복잡하지 않은 정면 또는 대표 사진을 권장합니다.",
    }


def _encode_image(image_path: str) -> np.ndarray:
    model, preprocess = _load_model()
    image = Image.open(image_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(_device)

    with torch.no_grad():
        image_feature = model.encode_image(image_input)
        image_feature /= image_feature.norm(dim=-1, keepdim=True)

    return image_feature.cpu().numpy()[0].astype(np.float32)


def search_similar_images(image_path: str, top_k: int = 5) -> List[Dict[str, object]]:
    validate_query_image(image_path)
    data = _load_embeddings()

    embeddings = np.asarray(data["embeddings"], dtype=np.float32)
    items = data["items"]
    if embeddings.size == 0 or not items:
        return []

    query_embedding = _encode_image(image_path)
    scores = embeddings @ query_embedding

    ranked_indices = np.argsort(scores)[::-1]

    results = []
    for idx in ranked_indices:
        score = float(scores[idx])
        if score < MIN_SCORE:
            continue

        item = dict(items[idx])
        item["score"] = score
        results.append(item)

        if len(results) >= top_k:
            break

    return results