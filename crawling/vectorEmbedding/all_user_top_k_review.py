import os
import json
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes import query as wq


# ========== CONFIG ==========
CONFIG = {
    "USER_FILE": r"C:\Users\changjin\workspace\lab\pln\data_set\5_user_info.csv",
    "DATA_DIR": r"C:\Users\changjin\workspace\lab\pln\data_set\null_X",
    "OUTPUT_DIR": r"C:\Users\changjin\workspace\lab\pln\vectorEmbedding\user_results",
    "TOP_K": 30,
    "GAMMA": 0.3   # 리뷰수 가중치
}

CATEGORY_FILES = {
    "Accommodation": "accommodations_fixed.csv",
    "카페": "cafe_fixed.csv",
    "음식점": "restaurants_fixed.csv",
    "관광지": "attractions_fixed.csv"
}

# 카테고리 한글 → 영어 변환 매핑
CATEGORY_TRANSLATE = {
    "Accommodation": "Accommodation",
    "카페": "Cafe",
    "음식점": "Restaurant",
    "관광지": "Attraction"
}


# ========== 1. 환경 변수 및 클라이언트 연결 ==========
print("🔐 환경 변수 로딩...")
load_dotenv()

api_key = os.getenv("WEAVIATE_API_KEY")
cluster_url = os.getenv("WEAVIATE_CLUSTER_URL")

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=cluster_url,
    auth_credentials=AuthApiKey(api_key)
)
print("✅ Weaviate 연결 완료\n")

collection = client.collections.get("Place")


# ========== 2. 모델 로드 ==========
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")


# ========== 3. 추천 함수 ==========
def rerank_with_penalty(user_like_vec, user_dislike_vecs, category_name,
                        top_k=30, alpha=1.0, beta=0.5, dislike_threshold=0.75):
    results = collection.query.near_vector(
        near_vector=user_like_vec.tolist(),
        limit=top_k*3,
        return_metadata=["distance"],
        include_vector=True,
        filters=wq.Filter.by_property("category").equal(category_name)
    )

    scored = []
    for obj in results.objects:
        like_sim = 1 - obj.metadata.distance

        place_dislike_vec = obj.properties.get("dislike_embedding", [])
        max_dislike_sim = 0
        if place_dislike_vec:
            sims = [
                cosine_similarity([ud], [place_dislike_vec])[0][0]
                for ud in user_dislike_vecs if len(ud) > 0
            ]
            max_dislike_sim = max(sims) if sims else 0

        if max_dislike_sim > dislike_threshold:
            continue

        sim_score = alpha * like_sim - beta * max_dislike_sim
        scored.append((obj, sim_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# ========== 4. 리뷰수 기반 정규화 + 최종 스코어 ==========
def attach_review_scores_and_final(results_by_cat, data_dir, gamma=0.3):
    final_scores = {}

    for cat, scored_list in results_by_cat.items():
        if not scored_list:
            continue

        df = pd.read_csv(os.path.join(data_dir, CATEGORY_FILES[cat]))
        review_col = "review_count" if cat == "Accommodation" else "all_review_count"
        review_dict = dict(zip(df["id"], df[review_col]))

        enriched = []
        for obj, sim_score in scored_list:
            pid = obj.properties.get("place_id")
            rc = review_dict.get(pid, 0)
            enriched.append((pid, sim_score, rc))

        counts = np.array([rc for _, _, rc in enriched], dtype=float)
        if counts.sum() > 0:
            counts = np.log1p(counts)
            exp_counts = np.exp(counts - counts.max())
            review_norms = exp_counts / exp_counts.sum()
        else:
            review_norms = np.ones(len(enriched)) / len(enriched)

        cat_list = []
        for (pid, sim_score, _), rn in zip(enriched, review_norms):
            final_score = (1 - gamma) * sim_score + gamma * rn
            cat_list.append({
                "id": pid,
                "category": CATEGORY_TRANSLATE[cat],  # ✅ 영어 변환
                "final_score": float(final_score)
            })

        cat_list = sorted(cat_list, key=lambda x: x["final_score"], reverse=True)

        # ✅ key 자체도 영어로 변환
        final_scores[CATEGORY_TRANSLATE[cat]] = cat_list

    return final_scores


# ========== 5. 모든 유저 처리 ==========
user_df = pd.read_csv(CONFIG["USER_FILE"])
os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)

for idx, user in user_df.iterrows():
    user_id = user["user_id"]
    like_keywords = eval(user["like_keywords"])
    dislike_keywords = eval(user["dislike_keywords"])

    print(f"\n👤 Processing User {idx+1}/{len(user_df)} → {user_id}")
    print("   👍 like:", like_keywords)
    print("   👎 dislike:", dislike_keywords)

    user_like_vec = model.encode(" ".join(like_keywords), convert_to_numpy=True)
    user_dislike_vecs = [model.encode(kw, convert_to_numpy=True) for kw in dislike_keywords]

    results_by_cat = {}
    for cat in CATEGORY_FILES.keys():
        results_by_cat[cat] = rerank_with_penalty(user_like_vec, user_dislike_vecs,
                                                  cat, top_k=CONFIG["TOP_K"])

    review_scores_by_cat = attach_review_scores_and_final(results_by_cat,
                                                          CONFIG["DATA_DIR"],
                                                          gamma=CONFIG["GAMMA"])

    # 유저별 결과 저장
    out_path = os.path.join(CONFIG["OUTPUT_DIR"], f"{user_id}_recommendations.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(review_scores_by_cat, f, ensure_ascii=False, indent=2)

    print(f"✅ {user_id} 결과 저장 완료 → {out_path}")


# ========== 6. 연결 종료 ==========
client.close()
print("\n🔒 전체 유저 처리 완료 & 연결 종료")
