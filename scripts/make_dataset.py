# scripts/make_dataset.py

# python -m scripts.make_dataset ^
#   --input data/output/naver_cafe_titles.json ^
#   --output data/output/dataset_ad.csv ^
#   --label "광고" ^
#   --sep " " ^
#   --require-body

from __future__ import annotations

import argparse
import csv
import json
import os
from typing import List, Dict, Any, Iterable


def load_rows(path: str) -> List[Dict[str, Any]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "rows" in data:
                return data["rows"]  # 혹시 {"rows":[...]} 형태도 허용
            if isinstance(data, list):
                return data
            raise ValueError("Unsupported JSON structure")
    elif ext == ".csv":
        with open(path, "r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    else:
        raise ValueError("Input must be .json or .csv")


def normalize_text(x: Any) -> str:
    if not x:
        return ""
    s = str(x).strip()
    # 줄바꿈/탭 정리
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ").strip()
    # 너무 많은 공백 축소
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def build_sentence(r: Dict[str, Any], sep: str = " ") -> str:
    body = normalize_text(r.get("content_text", ""))
    return body


def filter_valid(rows: Iterable[Dict[str, Any]], require_body: bool) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        body = normalize_text(r.get("content_text", ""))
        if require_body and not body:
            continue
        if not body:
            continue
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description="naver_cafe_scraper 결과를 Sentence,Label 형식으로 변환 (content_text만 사용)")
    ap.add_argument("--input", required=True, help="크롤 결과 경로 (.json 또는 .csv)")
    ap.add_argument("--output", required=True, help="저장할 CSV 경로")
    ap.add_argument("--label", default="", help="모든 레코드에 넣을 Label 값 (예: 광고)")
    ap.add_argument("--sep", default=" ", help="(미사용) title과 content_text 구분자 — 현재 content_text만 사용")
    ap.add_argument("--require-body", action="store_true", help="content_text 없는 항목 제외")
    ap.add_argument("--max-chars", type=int, default=0, help="문장 길이 상한(0=제한 없음)")
    args = ap.parse_args()

    rows = load_rows(args.input)
    rows = filter_valid(rows, require_body=args.require_body)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Sentence", "Label"])
        for r in rows:
            sent = build_sentence(r, sep=args.sep)  # content_text만 반환
            if args.max_chars and len(sent) > args.max_chars:
                sent = sent[: args.max_chars].rstrip() + "…"
            writer.writerow([sent, args.label])

    print(f"[done] wrote {len(rows)} rows -> {args.output}")


if __name__ == "__main__":
    main()
