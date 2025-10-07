import json
import time
import random
import re
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

INPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_3_latlng.jsonl"
OUTPUT_PATH = (
    r"/Users/changjin/Desktop/Workspace/lab/sac/cafe/all_data_4_store_hours.jsonl"
)


def setup_driver():
    """웹드라이버 설정"""
    options = webdriver.ChromeOptions()
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # GPU/WebGL 에러 메시지 제거
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")

    # 로그 메시지 완전히 차단
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    return driver


def extract_day_and_time(text):
    """텍스트에서 요일과 시간만 추출"""
    # 매일/전체 요일 키워드 체크
    everyday_keywords = [
        "매일",
        "전일",
        "연중무휴",
        "매주",
        "전체",
        "모든요일",
        "모든 요일",
        "월~일",
        "월-일",
    ]
    is_everyday = any(keyword in text for keyword in everyday_keywords)

    if is_everyday:
        # 시간 패턴 추출
        time_pattern = re.findall(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", text)
        if time_pattern:
            # 모든 요일에 같은 시간 적용
            all_days = ["월", "화", "수", "목", "금", "토", "일"]
            return "everyday", time_pattern[0]  # 특별한 키워드로 반환

    # 일반적인 요일 추출
    days = ["월", "화", "수", "목", "금", "토", "일"]
    day = None
    for d in days:
        if d in text:
            day = d
            break

    # 1. 휴무 키워드가 명시적으로 있는지 체크
    rest_keywords = ["휴무", "정기휴무", "휴무일", "closed", "운영안함", "영업안함"]
    if any(keyword in text.lower() for keyword in rest_keywords):
        return day, "휴무"

    # 2. 시간 패턴 추출 (숫자:숫자 형태)
    time_pattern = re.findall(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", text)
    if time_pattern:
        time_info = time_pattern[0]
    else:
        # 대안: 숫자가 포함된 시간 정보 찾기
        parts = text.split()
        time_parts = []
        for part in parts:
            if ":" in part and any(char.isdigit() for char in part):
                time_parts.append(part)
            elif "-" in part and any(char.isdigit() for char in part):
                time_parts.append(part)
        time_info = " ".join(time_parts) if time_parts else None

    # 3. 요일은 있는데 시간이 없으면 휴무로 처리 (요일별 개별 판단)
    if day and not time_info:
        time_info = "휴무"

    return day, time_info


def get_store_hours(url, driver):
    """운영시간 정보 추출"""
    # URL 변환
    if "m.place.naver.com" in url:
        match = re.search(r"/restaurant/(\d+)", url)
        if match:
            place_id = match.group(1)
            home_url = f"https://pcmap.place.naver.com/restaurant/{place_id}/home"
        else:
            return None
    else:
        home_url = url.replace("/review", "/home")

    store_hours = []

    try:
        driver.get(home_url)
        time.sleep(3)

        # 운영시간 컨테이너 찾기
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.O8qbU.pSavy"))
        )

        # 펼치기 버튼 클릭
        try:
            toggle_btn = container.find_element(
                By.CSS_SELECTOR, 'a[role="button"][aria-expanded="false"]'
            )
            driver.execute_script("arguments[0].click();", toggle_btn)
            time.sleep(1)
        except:
            pass

        # 시간 블록들 찾기
        try:
            inner_container = container.find_element(By.CLASS_NAME, "vV_z_")
            time_blocks = inner_container.find_elements(By.CLASS_NAME, "w9QyJ")

            # 요일별로 결과 저장 (중복 방지)
            day_hours = {}

            for block in time_blocks:
                text = block.text.strip().replace("\n", " ")
                day, time_info = extract_day_and_time(text)

                if day == "everyday" and time_info:
                    # 매일인 경우 모든 요일에 적용
                    all_days = ["월", "화", "수", "목", "금", "토", "일"]
                    for d in all_days:
                        day_hours[d] = time_info
                elif day and time_info:
                    # 시간 정보가 있는 것을 우선 (휴무보다 실제 시간을 우선)
                    if day not in day_hours or (
                        day_hours[day] == "휴무" and time_info != "휴무"
                    ):
                        day_hours[day] = time_info

            # 결과를 리스트로 변환
            for day, hours in day_hours.items():
                store_hours.append(f"{day}: {hours}")

        except:
            # 대안: 페이지 전체에서 요일+시간 패턴 찾기
            page_elements = driver.find_elements(
                By.XPATH,
                "//*[contains(text(), '월') or contains(text(), '화') or contains(text(), '수') or contains(text(), '목') or contains(text(), '금') or contains(text(), '토') or contains(text(), '일')]",
            )

            # 요일별로 결과 저장 (중복 방지)
            day_hours = {}

            for element in page_elements:
                text = element.text.strip().replace("\n", " ")
                if len(text) < 50:
                    day, time_info = extract_day_and_time(text)

                    if day == "everyday" and time_info:
                        # 매일인 경우 모든 요일에 적용
                        all_days = ["월", "화", "수", "목", "금", "토", "일"]
                        for d in all_days:
                            day_hours[d] = time_info
                    elif day and time_info:
                        # 시간 정보가 있는 것을 우선 (휴무보다 실제 시간을 우선)
                        if day not in day_hours or (
                            day_hours[day] == "휴무" and time_info != "휴무"
                        ):
                            day_hours[day] = time_info

            # 결과를 리스트로 변환
            for day, hours in day_hours.items():
                store_hours.append(f"{day}: {hours}")

        return store_hours if store_hours else None

    except Exception as e:
        print(f"오류: {e}")
        return None


def process_jsonl(input_path, output_path):
    """JSONL 파일 처리"""
    driver = setup_driver()

    try:
        with open(input_path, "r", encoding="utf-8") as infile:
            lines = [line.strip() for line in infile if line.strip()]

        success_count = 0

        with open(output_path, "w", encoding="utf-8") as outfile:
            for i, line in enumerate(tqdm(lines, desc="크롤링 중")):
                data = json.loads(line)

                # place_id로 URL 생성
                place_id = data.get("place_id")
                if place_id:
                    url = f"https://pcmap.place.naver.com/restaurant/{place_id}/home"
                    store_hours = get_store_hours(url, driver)

                    if store_hours:
                        success_count += 1
                        print(
                            f"성공 ({i+1}/{len(lines)}): {data.get('place_name', '')} - {len(store_hours)}개"
                        )
                else:
                    store_hours = None

                data["store_hours"] = store_hours
                outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

                time.sleep(random.uniform(1, 2))

    finally:
        driver.quit()

    print(f"완료: 총 {len(lines)}개 중 {success_count}개 성공")


if __name__ == "__main__":
    process_jsonl(INPUT_PATH, OUTPUT_PATH)
