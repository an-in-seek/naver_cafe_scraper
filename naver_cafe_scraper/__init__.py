"""
naver_cafe_scraper 패키지
-------------------------
네이버 카페 게시글 목록을 크롤링하고 CSV/JSON 등으로 저장하는 기능을 제공합니다.

모듈 구성:
- config.py    : 환경설정 및 경로 정의
- crawler.py   : 크롤러 클래스(CafeCrawler)
- parser.py    : HTML 파싱 로직
- exporter.py  : CSV/JSON 저장 유틸
- utils.py     : 공통 유틸 함수
- login.py     : 네이버 로그인 세션 처리
"""

from .config import (
    BASE_URL,
    MAX_PAGES,
    STATE_PATH,
    HEADLESS,
    WAIT_MS,
    REQUEST_DELAY_SEC,
    DEBUG,
)
from .crawler import CafeCrawler
from .exporter import save_csv, save_json
from .parser import extract_posts_from_frame

__all__ = [
    # 설정 상수
    "BASE_URL",
    "MAX_PAGES",
    "STATE_PATH",
    "HEADLESS",
    "WAIT_MS",
    "REQUEST_DELAY_SEC",
    "DEBUG",
    # 주요 클래스/함수
    "CafeCrawler",
    "extract_posts_from_frame",
    "save_csv",
    "save_json",
]
