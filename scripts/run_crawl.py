# scripts/run_crawl.py
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from naver_cafe_scraper import CafeCrawler, save_csv, save_json
from naver_cafe_scraper import config as cfg
from naver_cafe_scraper.utils import ensure_dir


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--pages", type=int, default=cfg.MAX_PAGES, help="수집할 페이지 수")
    p.add_argument(
        "--output",
        type=str,
        default=os.path.join(cfg.BASE_DIR, "data", "output", "naver_cafe_titles.csv"),
        help="CSV 저장 경로",
    )
    p.add_argument(
        "--json",
        type=str,
        default=None,
        help="JSON 저장 경로(선택). 지정 시 CSV와 함께 저장",
    )
    p.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="게시판 목록 시작 URL (미지정 시 config.BASE_URL 사용)",
    )
    p.add_argument(
        "--detail",
        action="store_true",
        help="상세 페이지(본문/이미지/외부링크 등)까지 함께 수집",
    )
    p.add_argument(
        "--progress",
        action="store_true",
        help="콘솔에 진행상황(진척도) 표시",
    )
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()

    # base_url 기본값을 config에서 채움
    base_url = args.base_url or cfg.BASE_URL

    crawler = CafeCrawler(
        base_url=base_url,
        headless=cfg.HEADLESS,
        state_path=cfg.STATE_PATH,
        wait_ms=cfg.WAIT_MS,
    )

    rows = crawler.collect(
        max_pages=args.pages,
        base_url=base_url,
        fetch_detail=args.detail,
        per_detail_delay_sec=0.5,
        show_progress=args.progress,  # ← 진척도 표시
    )

    # 저장
    if args.output:
        ensure_dir(os.path.dirname(args.output))
        save_csv(rows, args.output)
        print(f"[save] CSV: {args.output}")

    if args.json:
        ensure_dir(os.path.dirname(args.json))
        save_json(rows, args.json)
        print(f"[save] JSON: {args.json}")

    print(f"[done] 총 {len(rows)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
