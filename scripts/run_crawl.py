#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from naver_cafe_scraper import config as cfg
from naver_cafe_scraper import CafeCrawler, save_csv, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="네이버 카페 게시글 크롤러 실행")
    parser.add_argument(
        "--pages",
        type=int,
        default=cfg.MAX_PAGES,
        help=f"수집할 페이지 수 (default: {cfg.MAX_PAGES})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=cfg.DEFAULT_OUTPUT_CSV,
        help=f"CSV 저장 경로 (default: {cfg.DEFAULT_OUTPUT_CSV})",
    )
    parser.add_argument(
        "--json", type=str, default=None, help="JSON 저장 경로 (지정 시 JSON도 저장)"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=cfg.BASE_URL,
        help=f"크롤링 시작 URL (default: {cfg.BASE_URL})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    crawler = CafeCrawler(
        base_url=args.base_url,
        headless=cfg.HEADLESS,
        state_path=cfg.STATE_PATH,
        wait_ms=cfg.WAIT_MS,
    )

    rows = crawler.collect(max_pages=args.pages, base_url=args.base_url)
    if not rows:
        print("[run_crawl] 수집된 데이터가 없습니다.")
        return 1

    # CSV 저장
    csv_path = save_csv(rows, path=args.output)
    print(f"[run_crawl] CSV 저장 완료: {csv_path}")

    # JSON 저장 (선택)
    if args.json:
        json_path = save_json(rows, path=args.json)
        print(f"[run_crawl] JSON 저장 완료: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
