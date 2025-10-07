# ❌ 실패 항목들:

# 실패 항목들 수작업 스타트

# [10]add_latlng.py
import json
from pathlib import Path
import requests
from tqdm import tqdm

# ========= 카카오 REST API 키 =========
# KAKAO_REST_API_KEY = ""


def get_coordinates(address: str):
    """
    카카오 로컬 API를 이용해 주소를 위도/경도로 변환
    """
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": address}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
    except Exception as e:
        print("Request error:", e)
        return None, None

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None, None

    data = response.json()
    if data.get("documents"):
        x = data["documents"][0]["x"]  # 경도
        y = data["documents"][0]["y"]  # 위도
        return float(y), float(x)
    else:
        return None, None


# ========= 파일 경로 =========
INPUT_FILE = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_2_address.jsonl"
OUTPUT_FILE = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_3_latlng.jsonl"


def add_latlng(input_file: str, output_file: str):
    in_path = Path(input_file)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(in_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = updated = skipped = failed = 0
    failed_items = []

    with open(out_path, "w", encoding="utf-8") as fout, tqdm(
        total=len(lines), desc="Adding LatLng", unit="line"
    ) as pbar:
        for line in lines:
            total += 1
            try:
                obj = json.loads(line)
            except:
                pbar.update(1)
                continue

            # 이미 위경도가 있는 경우 스킵
            if obj.get("latitude") not in (None, "", "null") and obj.get(
                "longitude"
            ) not in (None, "", "null"):
                skipped += 1
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                pbar.update(1)
                continue

            address = obj.get("address")
            if not address:
                failed += 1
                failed_items.append(
                    {
                        "place_id": obj.get("place_id"),
                        "place_name": obj.get("place_name"),
                    }
                )
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                pbar.update(1)
                continue

            lat, lng = get_coordinates(address)
            if lat and lng:
                obj["latitude"] = lat
                obj["longitude"] = lng
                updated += 1
            else:
                failed += 1
                failed_items.append(
                    {
                        "place_id": obj.get("place_id"),
                        "place_name": obj.get("place_name"),
                        "address": address,
                    }
                )

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            pbar.update(1)

    print(f"\n✅ Done: {out_path}")
    print(
        f"총 {total}건 / 새로 채움 {updated}건 / 실패 {failed}건 / 기존 유지 {skipped}건"
    )
    if failed_items:
        print("\n❌ 실패 항목들:")
        for item in failed_items:
            print(
                f" - place_id: {item['place_id']} / place_name: {item['place_name']} / address: {item.get('address')}"
            )


if __name__ == "__main__":
    add_latlng(INPUT_FILE, OUTPUT_FILE)
