import pandas as pd
import os
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import json
import pickle

# 모델 로드
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# 경로 및 파일
path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
files = ["attractions_fixed.csv", "restaurants_fixed.csv", "accommodations_fixed.csv", "cafe_fixed.csv"]

# 결과 저장
embedding_results = []

# --- 키워드 분리 함수 ---
def split_keywords(keyword_str):
    if pd.isna(keyword_str):
        return []
    return [kw.strip() for kw in keyword_str.split(";") if kw.strip()]

# --- 각 파일 처리 ---
for fname in files:
    df = pd.read_csv(os.path.join(path, fname))

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Processing {fname}"):
        item_id = row.get("id")
        name = row.get("name", "")
        category = row.get("category", "")
        sub_category = row.get("sub_category", "")

        like_keywords = split_keywords(row.get("like", ""))
        dislike_keywords = split_keywords(row.get("dislike", ""))

        like_emb = model.encode(" ".join(like_keywords), convert_to_numpy=True).tolist() if like_keywords else []
        dislike_emb = model.encode(" ".join(dislike_keywords), convert_to_numpy=True).tolist() if dislike_keywords else []

        embedding_results.append({
            "id": item_id,
            "name": name,
            "category": category,
            "sub_category": sub_category,
            "like_embedding": like_emb,
            "dislike_embedding": dislike_emb
        })

# --- JSONL 저장 ---
jsonl_path = os.path.join(r"C:\Users\changjin\workspace\lab\pln\vectorEmbedding", "place_embeddings.jsonl")
with open(jsonl_path, "w", encoding="utf-8") as f_jsonl:
    for item in embedding_results:
        f_jsonl.write(json.dumps(item, ensure_ascii=False) + "\n")
print("✅ JSONL 저장 완료:", jsonl_path)

# --- Pickle 저장 ---
pkl_path = os.path.join(r"C:\Users\changjin\workspace\lab\pln\vectorEmbedding", "place_embeddings.pkl")
with open(pkl_path, "wb") as f_pkl:
    pickle.dump(embedding_results, f_pkl)
print("✅ Pickle 저장 완료:", pkl_path)
