import json

# 입력 및 출력 경로 설정
INPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_6_all_like.jsonl"
OUTPUT_PATH = (
    r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_7_all_like.jsonl"
)

with open(INPUT_PATH, "r", encoding="utf-8") as infile, open(
    OUTPUT_PATH, "w", encoding="utf-8"
) as outfile:

    for line in infile:
        data = json.loads(line)

        # 'like' → 'likes'
        if "like" in data:
            data["likes"] = data["like"]
            del data["like"]

        # 'dislike' → 'dislikes'
        if "dislike" in data:
            data["dislikes"] = data["dislike"]
            del data["dislike"]

        # 결과 쓰기
        outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

print("✅ 키 변경 완료! 저장 경로:", OUTPUT_PATH)
