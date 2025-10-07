

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

# ========== 1. 환경변수 로드 ==========
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ========== 2. 프롬프트 정의 ==========
SYSTEM_PROMPT = """여행 일정 JSON 생성기입니다.

출력 형식:
{
  "budget_per_day": 전체예산/일수,
  "itinerary": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "travel_day": "월",
      "season": "peak",
      "is_weekend": false,
      "transport": "car",
      "place_plan": [
        {"category": "Accommodation", "count": 1, "time": "09:30"},
        {"category": "Cafe", "count": 1, "time": "10:30"},
        ...
      ]
    }
  ]
}

규칙:
1. 모든 날 첫 활동 = Accommodation (숙소 출발)
2. 마지막 날 제외하고 마지막 활동 = Accommodation (숙소 귀환)
3. 마지막 날은 Accommodation 귀환 없음
4. travel_day = 월, 화, 수, 목, 금, 토, 일 중 하나
5. season = 7,8,12,1월이면 "peak", 나머지는 "offpeak"
6. is_weekend = 금요일 또는 토요일이면 true, 나머지 false

시간대 (나이별):
- 10~20대: 09:30~18:30
- 30~40대: 08:30~19:00
- 50대+: 08:00~18:30

스타일별 활동 개수 (하루 기준):
- Healing: Attraction 1~2, Cafe 1~2, Restaurant 2
- Foodie: Attraction 1~2, Cafe 1~2, Restaurant 3
- Activity: Attraction 3~4, Cafe 1, Restaurant 1
- Cultural: Attraction 2~3, Cafe 1, Restaurant 2

예시 (첫날):
{"category": "Accommodation", "count": 1, "time": "09:30"}
{"category": "Cafe", "count": 1, "time": "10:30"}
{"category": "Attraction", "count": 1, "time": "12:00"}
{"category": "Restaurant", "count": 1, "time": "13:30"}
{"category": "Attraction", "count": 1, "time": "15:00"}
{"category": "Restaurant", "count": 1, "time": "18:00"}
{"category": "Accommodation", "count": 1, "time": "19:00"}

마지막 날은 마지막 Accommodation 빼고.

순수 JSON만 출력하세요. 마크다운 코드블록(```) 사용 금지."""

# ========== 3. 유틸 함수 ==========
def get_date_info(date_str):
    """날짜 문자열로부터 요일, 시즌, 주말 여부 계산"""
    weekday_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    month = date_obj.month
    weekday_idx = date_obj.weekday()
    
    travel_day = weekday_map[weekday_idx]
    season = "peak" if month in [7, 8, 12, 1] else "offpeak"
    is_weekend = weekday_idx in [4, 5]  # 금(4), 토(5)
    
    return travel_day, season, is_weekend

# ========== 4. 함수 정의 ==========
def generate_itinerary(user_profile: dict):
    """
    user_profile: {
        "budget": 2200000,
        "duration_days": 3,
        "travel_style": "Healing",
        "age": 19,
        "gender": "Male",
        "start_date": "2025-08-16"
    }
    """
    # 날짜 정보 미리 계산
    start_date = datetime.strptime(user_profile['start_date'], "%Y-%m-%d")
    date_info_list = []
    
    for i in range(user_profile['duration_days']):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        travel_day, season, is_weekend = get_date_info(date_str)
        
        date_info_list.append({
            "day": i + 1,
            "date": date_str,
            "travel_day": travel_day,
            "season": season,
            "is_weekend": is_weekend
        })
    
    # 날짜 정보를 프롬프트에 포함
    date_info_text = "\n".join([
        f"Day {d['day']}: {d['date']} ({d['travel_day']}) - season: {d['season']}, weekend: {d['is_weekend']}"
        for d in date_info_list
    ])
    
    user_prompt = f"""
    유저 입력:
    - 전체 예산: {user_profile['budget']}
    - 여행 일수: {user_profile['duration_days']}
    - 여행 스타일: {user_profile['travel_style']}
    - 나이: {user_profile['age']}
    - 성별: {user_profile['gender']}
    - 출발일: {user_profile['start_date']}

    날짜별 정보:
    {date_info_text}

    위 날짜 정보의 travel_day, season, is_weekend를 정확히 사용해서 JSON으로 일정 생성하세요.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content.strip()
    
    # 마크다운 코드블록 제거
    if result_text.startswith("```"):
        lines = result_text.split('\n')
        result_text = '\n'.join(lines[1:-1])
    
    try:
        result_json = json.loads(result_text)
        return result_json
    except Exception as e:
        print(f"⚠️ JSON 파싱 실패: {e}")
        print("원본 텍스트:")
        print(result_text)
        return None

# ========== 5. 실행 예시 ==========
if __name__ == "__main__":
    user_profile = {
        "budget": 2200000,
        "duration_days": 3,
        "travel_style": "Healing",
        "age": 19,
        "gender": "Male",
        "start_date": "2025-08-16"
    }

    print("🔄 일정 생성 중...")
    itinerary = generate_itinerary(user_profile)
    
    if itinerary:
        print("\n✅ 생성 완료!\n")
        print(json.dumps(itinerary, ensure_ascii=False, indent=2))
        
        # 파일로도 저장
        with open("itinerary.json", "w", encoding="utf-8") as f:
            json.dump(itinerary, f, ensure_ascii=False, indent=2)
        print("\n💾 itinerary.json 파일로 저장됨")
    else:
        print("\n❌ 생성 실패")