# summarize_place_prefs_llm_only.py
import os
import json
import argparse
from typing import List, Dict
from tqdm import tqdm

# langchain import (old/new 호환)
try:
    from langchain.chat_models import ChatOpenAI  # old
except Exception:
    from langchain_community.chat_models.openai import ChatOpenAI  # new

PROMPT_TEMPLATE = """You are given two keyword lists, "like" and "dislike", extracted from user reviews for a single place.
Use ONLY these lists to produce summarized keywords.

Input:
likes = {likes}
dislikes = {dislikes}

Your task:
1) Group semantically similar keywords.
2) Merge duplicates or near-duplicates into one concise representative keyword.
3) For BOTH likes and dislikes:
   - If there are enough items, output EXACTLY 5 representative keywords.
   - If fewer than 5 but at least 3 exist, output all available (3–4).
   - Only if fewer than 3 valid items exist, output exactly that number (0–2).
4) Each representative keyword must be 1–3 words, concise and descriptive.
5) Avoid redundancy. Do not output empty arrays unless there are truly zero valid items in the input.

Output requirements:
- Return a SINGLE-LINE JSON object (no markdown, no code fence).
- Schema (NOTE: the braces below describe the schema, not sample values):
  {{"place_id": "<PLACE_ID>", "place_name": "<PLACE_NAME>", "like": [...], "dislike": [...]}}

Place id: {place_id}
Place name: {place_name}
"""


def call_llm_summary(
    place_id: str,
    place_name: str,
    likes: List[str],
    dislikes: List[str],
    *,
    api_key: str,
    api_base: str = "https://api.openai.com/v1/",
    model_name: str = "gpt-4o",
    temperature: float = 0.0,
) -> Dict:
    llm = ChatOpenAI(
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base=api_base,
        model_name=model_name,
    )
    prompt = PROMPT_TEMPLATE.format(
        place_id=place_id,
        place_name=place_name,
        likes=likes,  # 가공 없이 그대로 전달
        dislikes=dislikes,  # 가공 없이 그대로 전달
    )
    resp = llm.predict(prompt).strip()

    # LLM이 단일 JSON 객체를 준다고 가정, 실패 시 최소 폴백(빈 배열만)
    try:
        data = json.loads(resp)
        return {
            "place_id": data.get("place_id", place_id),
            "place_name": data.get("place_name", place_name),
            "like": data.get("like", []),
            "dislike": data.get("dislike", []),
        }
    except Exception:
        return {
            "place_id": place_id,
            "place_name": place_name,
            "like": [],
            "dislike": [],
        }


def summarize_places(
    input_path: str,
    output_path: str,
    *,
    api_key: str,
    api_base: str = "https://api.openai.com/v1/",
    model_name: str = "gpt-4o",
):
    with open(output_path, "w", encoding="utf-8") as out_f, open(
        input_path, "r", encoding="utf-8"
    ) as f:
        for line in tqdm(f, desc="Summarizing places", unit="place"):
            if not line.strip():
                continue
            obj = json.loads(line)

            place_id = obj.get("place_id") or obj.get("id") or ""
            place_name = obj.get("place_name") or obj.get("name") or ""
            likes = obj.get("likes", []) or []
            dislikes = obj.get("dislikes", []) or []

            summarized = call_llm_summary(
                place_id=place_id,
                place_name=place_name,
                likes=likes,
                dislikes=dislikes,
                api_key=api_key,
                api_base=api_base,
                model_name=model_name,
                temperature=0.0,
            )

            # 사후 가공/클램프 없이 그대로 기록
            out_f.write(json.dumps(summarized, ensure_ascii=False) + "\n")

    print(f"[INFO] Saved: {output_path}")


if __name__ == "__main__":
    # Colab/Notebook 친화: 인자 없어도 기본 경로로 실행
    DEFAULT_INPUT = (
        r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_7_all_like.jsonl"
    )
    DEFAULT_OUTPUT = (
        r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/each_cafe_likes.jsonl"
    )
    from dotenv import load_dotenv
    import os, openai

    load_dotenv()
    API_KEY = os.getenv("OPENAI_API_KEY")
    if not API_KEY:
        raise RuntimeError(
            "Environment variable Gpt_API_KEY is empty. "
            "Set in Colab: %env Gpt_API_KEY=sk-..."
        )

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--input", help="path to input jsonl (optional)")
    parser.add_argument("--output", help="path to output jsonl (optional)")
    parser.add_argument("--api_base", default="https://api.openai.com/v1/")
    parser.add_argument("--model_name", default="gpt-4o")
    args, _ = parser.parse_known_args()

    input_path = args.input or DEFAULT_INPUT
    output_path = args.output or DEFAULT_OUTPUT

    print(f"[INFO] Using input:  {input_path}")
    print(f"[INFO] Using output: {output_path}")

    summarize_places(
        input_path=input_path,
        output_path=output_path,
        api_key=API_KEY,
        api_base=args.api_base,
        model_name=args.model_name,
    )

    print(f"[INFO] Done. Saved -> {output_path}")
