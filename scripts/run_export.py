#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

# 프로젝트 루트 경로를 sys.path에 추가
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from naver_cafe_scraper import exporter  # save_csv, save_json, save_parquet


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="크롤링 결과 포맷 변환")
    p.add_argument("--input", required=True, help="입력 파일 경로 (CSV 또는 JSON)")
    p.add_argument("--format", required=True, choices=["csv", "json", "parquet"], help="출력 포맷")
    p.add_argument("--output", help="출력 경로(미지정 시 입력 경로의 확장자만 교체)")
    p.add_argument(
        "--fields",
        help="출력 컬럼 순서 지정 (예: page,article_no,head,title,url,author,date,read_count,like_count)",
    )
    p.add_argument("--json-orient", default="records", help="JSON 저장 시 orient (기본: records)")
    return p.parse_args()


def _load_rows(src: Path) -> list[dict]:
    if src.suffix.lower() == ".csv":
        df = pd.read_csv(src)
        return df.to_dict(orient="records")
    elif src.suffix.lower() == ".json":
        # records 형태 권장, 기타 형태면 자동 변환 시도
        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
            # list[dict]가 아니면 DataFrame 통해 정규화
            if isinstance(data, list) and (not data or isinstance(data[0], dict)):
                return data
            return pd.json_normalize(data).to_dict(orient="records")
        except Exception:
            # pandas로 재시도 (예: json lines가 아닌 특수 포맷 대응)
            df = pd.read_json(src)
            return df.to_dict(orient="records")
    else:
        raise ValueError(f"지원하지 않는 입력 확장자: {src.suffix}")


def main() -> int:
    args = parse_args()
    src = Path(args.input)
    if not src.exists():
        print(f"[ERR] 입력 파일이 없습니다: {src}")
        return 1

    rows = _load_rows(src)
    fields = [s.strip() for s in args.fields.split(",")] if args.fields else None

    # 출력 경로 결정
    if args.output:
        dst = Path(args.output)
    else:
        dst = src.with_suffix("." + args.format)

    dst.parent.mkdir(parents=True, exist_ok=True)

    # 저장
    if args.format == "csv":
        out = exporter.save_csv(rows, path=str(dst), fields=fields)
    elif args.format == "json":
        # exporter.save_json은 ensure_ascii=False, indent=2 기본
        out = exporter.save_json(rows, path=str(dst), fields=fields)
    else:  # parquet
        out = exporter.save_parquet(rows, path=str(dst), fields=fields)

    print(f"[OK] exported: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
