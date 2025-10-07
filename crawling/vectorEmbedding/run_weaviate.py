import os
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Property, DataType
import pickle
from tqdm import tqdm
import uuid

# --- 1. 환경 변수 로드 ---
load_dotenv()

api_key = os.getenv("WEAVIATE_API_KEY")
cluster_url = os.getenv("WEAVIATE_CLUSTER_URL")

# --- 2. Weaviate 클라이언트 연결 (v4 방식) ---
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=cluster_url,
    auth_credentials=AuthApiKey(api_key)
)
print("✅ 연결 성공")

try:
    # --- 3. 기존 컬렉션 있으면 삭제 (선택 사항) ---
    collection_name = "Place"
    if client.collections.exists(collection_name):
        client.collections.delete(collection_name)
        print("♻️ 기존 컬렉션 삭제 완료")

    # --- 4. 스키마(컬렉션) 생성 ---
    from weaviate.classes.config import Configure, VectorDistances
    
    client.collections.create(
        name=collection_name,
        vectorizer_config=None,  # 직접 벡터 제공
        vector_index_config=Configure.VectorIndex.hnsw(
            distance_metric=VectorDistances.COSINE  # 코사인 유사도
        ),
        properties=[
            Property(name="place_id", data_type=DataType.INT),  # 원본 ID 보존
            Property(name="name", data_type=DataType.TEXT),
            Property(name="category", data_type=DataType.TEXT),
            Property(name="sub_category", data_type=DataType.TEXT),
            Property(name="dislike_embedding", data_type=DataType.NUMBER_ARRAY)
        ]
    )
    print("✅ 컬렉션 생성 완료")

    # --- 5. Pickle 파일 로드 ---
    pkl_path = r"C:\Users\changjin\workspace\lab\pln\vectorEmbedding\place_embeddings.pkl"
    with open(pkl_path, "rb") as f:
        data = pickle.load(f)

    # --- 6. 데이터 업로드 ---
    collection = client.collections.get(collection_name)
    
    # 벡터 차원 확인 (첫 번째 유효한 벡터에서)
    vector_dim = None
    for item in data:
        if item.get("like_embedding"):
            vector_dim = len(item["like_embedding"])
            break
    
    if vector_dim is None:
        raise ValueError("유효한 벡터를 찾을 수 없습니다.")
    
    print(f"📐 벡터 차원: {vector_dim}")

    for item in tqdm(data, desc="Weaviate 업로드 중"):
        # 벡터가 없으면 제로 벡터로 대체
        vector = item.get("like_embedding")
        if not vector or len(vector) == 0:
            vector = [0.0] * vector_dim
        
        collection.data.insert(
            properties={
                "place_id": item["id"],  # 원본 ID 저장
                "name": item["name"],
                "category": item["category"],
                "sub_category": item["sub_category"],
                "dislike_embedding": item.get("dislike_embedding", [])
            },
            vector=vector
        )

    print("✅ 데이터 업로드 완료")

finally:
    # --- 7. 연결 종료 ---
    client.close()
    print("🔒 연결 종료")