import csv
import ast

INPUT_PATH = "/Users/changjin/Desktop/Workspace/lab/sac/cafe/cafe.csv"  # 원본 CSV
OUTPUT_PATH = "/Users/changjin/Desktop/Workspace/lab/sac/cafe/cleaned_cafe.csv"  # 정리된 CSV 저장 경로


def clean_field(value):
    if not value:
        return ""

    # 1) 리스트 같은 문자열 ("[""금...""]") → 파이썬 리스트로 변환
    if value.strip().startswith("[") and value.strip().endswith("]"):
        try:
            parsed = ast.literal_eval(value)  # 문자열을 리스트로 안전하게 변환
            if isinstance(parsed, list):
                return "; ".join(
                    map(str, parsed)
                )  # 리스트를 세미콜론 구분 문자열로 변환
        except:
            return value  # 변환 실패하면 원래 값 반환

    return value


with open(INPUT_PATH, "r", encoding="utf-8") as infile, open(
    OUTPUT_PATH, "w", encoding="utf-8", newline=""
) as outfile:

    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)

    writer.writeheader()

    for row in reader:
        cleaned_row = {k: clean_field(v) for k, v in row.items()}
        writer.writerow(cleaned_row)

print(f"✅ CSV 정리 완료: {OUTPUT_PATH}")
