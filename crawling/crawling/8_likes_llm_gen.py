import json
import os
from tqdm import tqdm
from typing import List, Tuple

from langchain.chat_models import ChatOpenAI

from dotenv import load_dotenv
import os, openai

load_dotenv()


# -----------------------------
# 1. LLM 호출
# -----------------------------
def generate_likes_dislikes(review_text: str, api_config: dict, model_name: str) -> str:
    """
    Call ChatOpenAI to generate [Like]/[Dislike] for attractions based on review_text.
    Return an empty string if an exception occurs.
    """
    try:
        llm = ChatOpenAI(
            temperature=0,
            openai_api_key=api_config[model_name]["api_key"],
            openai_api_base=api_config[model_name]["url"],
            model_name=api_config[model_name]["model"],
        )

        input_text = (
            "<|begin_of_text|><|start_header_id|>system<|end_header_id|>"
            "Given a review written by a user, list the preferences the user liked and disliked about the restaurant under [Like] and [Dislike] in bullet points, respectively. "
            "If there is nothing to mention about like/dislike, simply write 'None' under the corresponding tag. "
            "DO NOT write any content that is not revealed in the review. Please do not repeat the expressions in the original text, but use one or more words to describe the characteristics of the restaurants that the user is interested in.\n"
            "Analyze user reviews of restaurants.\n"
            "List preferences under [Like]/[Dislike] using these strict criteria:\n"
            "1. Focus on: Food & Taste, Service, Facilities, Atmosphere, Value for Money\n"
            "2. EXCLUDE: Transportation, weather, personal scheduling, or off-site locations\n"
            "3. Require direct textual evidence in the review\n"
            "4. Express characteristics as concise descriptors (1-3 words)\n"
            "For EACH bullet point, validate:\n"
            "- Directly concerns the  restaurant's core features/services\n"
            "- Not affected by external/temporary factors\n"
            "- Not about adjacent locations/activities outside restaurant boundaries\n\n"
            "If no valid aspects exist for a section, output 'None'.\n"
            "Now, analyze the following review and extract meaningful likes and dislikes:\n"
            "### Output Format:\n"
            "[Like]\n"
            "- Encapsulate the preferences the user liked in bullet points.\n"
            "If no relevant likes found: None\n\n"
            "[Dislike]\n"
            "- Encapsulate the preferences the user disliked in bullet points.\n"
            "If no relevant dislikes found: None\n\n"
            f"Review: {review_text}\n"
            "The review text is written in Korean. Analyze the review in Korean, but your output must still follow the required English format ([Like]/[Dislike] with bullet points).\n"
            "<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        )

        response = llm.predict(input_text)
        return response
    except Exception as e:
        print(f"[ERROR] Error during LLM call: {e}")
        return ""


# -----------------------------
# 2. LLM 응답 파싱
# -----------------------------
def parse_likes_dislikes(llm_response: str) -> Tuple[List[str], List[str]]:
    """
    Extract [Like] and [Dislike] content from the LLM response text.
    Return (likes, dislikes) two lists.
    """
    likes = []
    dislikes = []

    like_section = False
    dislike_section = False

    for line in llm_response.split("\n"):
        if line.strip().startswith("[Like]"):
            like_section = True
            dislike_section = False
            continue
        if line.strip().startswith("[Dislike]"):
            like_section = False
            dislike_section = True
            continue

        if like_section and line.strip().startswith("-"):
            likes.append(line.strip("- ").strip())
        elif dislike_section and line.strip().startswith("-"):
            dislikes.append(line.strip("- ").strip())

    return likes, dislikes


# -----------------------------
# 3. JSONL 파일 처리
# -----------------------------
def process_reviews_in_jsonl(
    input_file: str, output_file: str, api_config: dict, model_name: str
):
    """
    JSONL 파일을 읽어서 reviews_attraction 안의 각 리뷰에 likes/dislikes를 추가
    """
    with open(input_file, "r", encoding="utf-8") as infile, open(
        output_file, "w", encoding="utf-8"
    ) as outfile:
        for line in tqdm(infile, desc="Processing places", unit="place"):
            data = json.loads(line.strip())

            if "reviews_attraction" in data:
                for review in tqdm(
                    data["reviews_attraction"],
                    desc="Processing reviews",
                    unit="review",
                    leave=False,
                ):
                    review_text = review.get("text", "").strip()
                    if review_text:
                        llm_response = generate_likes_dislikes(
                            review_text, api_config, model_name
                        )
                        likes, dislikes = parse_likes_dislikes(llm_response)
                        review["likes"] = likes
                        review["dislikes"] = dislikes

                        # ✅ 리뷰별 출력
                        print("\n--- 리뷰 분석 ---")
                        print(f"리뷰 원문: {review_text}")
                        print(f"Likes: {likes if likes else 'None'}")
                        print(f"Dislikes: {dislikes if dislikes else 'None'}")
                        print("----------------\n")

                    else:
                        review["likes"] = []
                        review["dislikes"] = []

            json.dump(data, outfile, ensure_ascii=False)
            outfile.write("\n")

    print(f"[INFO] 처리된 결과가 저장되었습니다: {output_file}")


# -----------------------------
# 4. 실행 부분
# -----------------------------
if __name__ == "__main__":
    api_config = {
        "gpt-4o": {
            "api_key": os.getenv("Gpt_API_KEY"),  # 환경 변수에서 API 키 읽음
            "url": "https://api.openai.com/v1/",
            "model": "gpt-4o",
        },
    }

    input_path = (
        r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_4_store_hours.jsonl"
    )
    output_path = (
        r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_5_llms.jsonl"
    )

    process_reviews_in_jsonl(
        input_file=input_path,
        output_file=output_path,
        api_config=api_config,
        model_name="gpt-4o",
    )
