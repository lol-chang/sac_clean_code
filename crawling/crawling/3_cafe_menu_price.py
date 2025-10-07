import json
import re
import statistics

# 입력/출력 파일 경로
INPUT_FILE = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/cafe_all_places.jsonl"
OUTPUT_FILE = (
    r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/cafe_all_places_with_prices.jsonl"
)

# 가격 정규식 (예: 3,000 원 / 50,000원 / ~3,000원)
price_pattern = re.compile(r"(\d{1,3}(?:,\d{3})*)\s*원")


def extract_prices(menu_list):
    """menu 리스트에서 가격 정수 리스트 추출"""
    prices = []
    for item in menu_list:
        matches = price_pattern.findall(item)
        for raw in matches:
            try:
                prices.append(int(raw.replace(",", "")))
            except:
                continue
    return prices if prices else None


def assign_price_fields(prices):
    """all_prices 기반으로 min/max/avg 계산"""
    if not prices:
        return None, None, None

    # 5000원 이상인 가격만 필터링
    filtered = [p for p in prices if p >= 5000]

    # 만약 필터링 결과가 비어 있으면 → 원래 prices 전체 사용
    target = filtered if filtered else prices

    min_price = min(target)
    max_price = max(target)
    avg_price = int(statistics.mean(target))

    return min_price, max_price, avg_price


def process_jsonl(input_file, output_file):
    """jsonl 읽어서 all_prices, min/max/avg 추가 후 저장"""
    with open(input_file, "r", encoding="utf-8") as fin, open(
        output_file, "w", encoding="utf-8"
    ) as fout:

        for line in fin:
            try:
                obj = json.loads(line)
                menu = obj.get("menu", [])

                if menu:
                    all_prices = extract_prices(menu)
                else:
                    all_prices = None

                obj["all_prices"] = all_prices

                # min/max/avg 업데이트
                if all_prices:
                    min_p, max_p, avg_p = assign_price_fields(all_prices)
                    obj["min_price"] = min_p
                    obj["max_price"] = max_p
                    obj["avg_price"] = avg_p
                else:
                    obj["min_price"] = None
                    obj["max_price"] = None
                    obj["avg_price"] = None

                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

            except Exception as e:
                print("JSON parse error:", e)

    print(f"✅ 완료: {output_file} 에 저장됨")


# 실행
if __name__ == "__main__":
    process_jsonl(INPUT_FILE, OUTPUT_FILE)
