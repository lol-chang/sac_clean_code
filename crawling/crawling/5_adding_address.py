# [8]adding_address_fast.py
import json
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import os
from tqdm import tqdm

# ========= 파일 경로 =========
INPUT_FILE = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_1.jsonl"
OUTPUT_FILE = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_2_address.jsonl"


# ========= 드라이버 생성 =========
def make_driver(headless=False, device_scale=0.4):
    options = webdriver.ChromeOptions()
    options.add_argument("window-size=1920x1080")
    options.add_argument(f"--force-device-scale-factor={device_scale}")
    options.add_argument("disable-gpu")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if headless:
        options.add_argument("--headless=new")

    null_log = "NUL" if sys.platform.startswith("win") else "/dev/null"
    service = Service(log_path=null_log)

    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(2)
    return driver


# ========= 주소 파싱 로직 =========
ADDR_CANDIDATE_SELECTORS = [
    "span._1vEbY",
    "span._1AJn9",
    "span._2yqUQ",
    '[data-nclicks-area-code="fwy_loc"] span',
    '[data-nclicks-area-code="fwy_loc"] a',
    "div.UCuLa span",
    "div.UCuLa a",
    "div.rAcDm span",
    "div.rAcDm a",
]

ADDR_PATTERN = re.compile(r"(?:도|시|군|구|읍|면|동|로|길)\s*\d")


def _pick_address_text(driver):
    """주소 텍스트 빠르게 탐색 (즉시)"""
    for sel in ADDR_CANDIDATE_SELECTORS:
        elems = driver.find_elements(By.CSS_SELECTOR, sel)
        for el in elems:
            txt = (el.text or "").strip()
            if not txt or "새 창이 열립니다" in txt or len(txt) < 5:
                continue
            if ADDR_PATTERN.search(txt):
                return txt
    return None


def scrape_address_from_place(
    driver, place_id: str, review_url: str | None = None
) -> str | None:
    """네이버 장소 → 주소 스크랩"""
    loc_url = f"https://m.place.naver.com/restaurant/{place_id}/location?entry=ple&reviewSort=recent"
    try:
        driver.get(loc_url)
    except Exception:
        if review_url:
            try:
                driver.get(review_url)
            except Exception:
                return None
        else:
            return None

    # 0.5초만 대기
    try:
        WebDriverWait(driver, 0.5).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    '[data-nclicks-area-code="fwy_loc"], div.UCuLa, div.rAcDm',
                )
            )
        )
    except Exception:
        pass

    # 즉시 탐색
    addr = _pick_address_text(driver)
    if addr:
        return addr

    # 폴백: 위치 섹션 텍스트 검사
    try:
        container = driver.find_element(
            By.CSS_SELECTOR, '[data-nclicks-area-code="fwy_loc"], div.UCuLa, div.rAcDm'
        )
        lines = [ln.strip() for ln in (container.text or "").splitlines() if ln.strip()]
        cand = [
            ln
            for ln in lines
            if "새 창이 열립니다" not in ln and ADDR_PATTERN.search(ln)
        ]
        if cand:
            cand.sort(key=len, reverse=True)
            return cand[0]
    except Exception:
        pass

    return None


# ========= JSONL 일괄 처리 =========
def fill_addresses(input_file: str, output_file: str, headless=False):
    in_path = Path(input_file)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    driver = make_driver(headless=headless)

    # tqdm 총 개수 위해 라인 수 세기
    with open(in_path, "r", encoding="utf-8") as f:
        total_lines = sum(1 for _ in f)

    total = updated = failed = skipped = 0

    with open(in_path, "r", encoding="utf-8") as fin, open(
        out_path, "w", encoding="utf-8"
    ) as fout, tqdm(total=total_lines, desc="Processing", unit="line") as pbar:

        for line in fin:
            total += 1
            try:
                obj = json.loads(line)
            except Exception as e:
                print("JSON parse error:", e)
                pbar.update(1)
                continue

            if obj.get("address") not in (None, "", "null"):
                skipped += 1
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                pbar.update(1)
                continue

            place_id = obj.get("place_id")
            review_url = obj.get("url")
            if not place_id:
                failed += 1
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                pbar.update(1)
                continue

            addr = scrape_address_from_place(
                driver, place_id=str(place_id), review_url=review_url
            )
            if addr:
                obj["address"] = addr
                updated += 1
            else:
                obj["address"] = None
                failed += 1

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            pbar.update(1)

    try:
        driver.quit()
    except Exception:
        pass

    print(f"\n✅ Done: {out_path}")
    print(
        f"총 {total}건 / 새로 채움 {updated}건 / 실패 {failed}건 / 기존 유지 {skipped}건"
    )


if __name__ == "__main__":
    fill_addresses(INPUT_FILE, OUTPUT_FILE, headless=False)
