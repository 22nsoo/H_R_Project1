import os
import pickle
import torch
import clip

from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

with open("embeddings.pkl", "rb") as f:
    data = pickle.load(f)

embeddings = data["embeddings"]
items = data["items"]


def search_similar_images(query_image_path, top_k=5):
    image = Image.open(query_image_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        query_feature = model.encode_image(image_input)
        query_feature /= query_feature.norm(dim=-1, keepdim=True)

    query_vec = query_feature.cpu().numpy()[0]
    sims = cosine_similarity([query_vec], embeddings)[0]
    top_idx = sims.argsort()[-top_k:][::-1]

    results = []
    for i in top_idx:
        results.append({
            "name": items[i]["name"],
            "brand": items[i]["brand"],
            "img": items[i]["img"],
            "score": float(sims[i]),
        })

    return results