import json

INPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_5_llms.jsonl"
OUTPUT_PATH = (
    r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_6_all_like.jsonl"
)


def merge_likes_dislikes(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as infile, open(
        output_path, "w", encoding="utf-8"
    ) as outfile:

        for line in infile:
            if not line.strip():
                continue

            data = json.loads(line)

            like_set = set(data["like"])
            unlike_set = set(data["dislike"])

            # reviews_attraction 내부의 likes/dislikes 합치기
            for review in data.get("reviews_attraction", []):
                for like_item in review.get("likes", []):
                    like_set.add(like_item)
                for dislike_item in review.get("dislikes", []):
                    unlike_set.add(dislike_item)

            data["like"] = list(like_set)
            data["dislike"] = list(unlike_set)

            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

    print(f"✅ 완료! 병합된 파일 저장됨: {output_path}")


if __name__ == "__main__":
    merge_likes_dislikes(INPUT_PATH, OUTPUT_PATH)
