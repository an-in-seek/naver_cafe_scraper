from __future__ import annotations

import os

# ===== 기본 설정 =====
# 크롤링 시작 URL (필요 시 환경변수로 교체)
BASE_URL: str = os.getenv(
    "NCS_BASE_URL",
    "https://cafe.naver.com/f-e/cafes/29434212/menus/77?page=1&size=15&viewType=L&headId=183",
)

# 가져올 페이지 수
MAX_PAGES: int = int(os.getenv("NCS_MAX_PAGES", "5"))

# 헤드리스 실행 여부 (서버/CI=True, 로컬 디버깅=False)
HEADLESS: bool = os.getenv("NCS_HEADLESS", "false").lower() in {"1", "true", "yes", "y"}

# 대기 시간(ms)
WAIT_MS: int = int(os.getenv("NCS_WAIT_MS", "20000"))  # 느린 환경 고려 default 20s

# 요청 간 딜레이(초) – 과도한 요청 방지
REQUEST_DELAY_SEC: float = float(os.getenv("NCS_REQUEST_DELAY_SEC", "1.0"))

# 디버그 출력 (프레임/네트워크 등 로그 도움)
DEBUG: bool = os.getenv("NCS_DEBUG", "false").lower() in {"1", "true", "yes", "y"}

# ===== 경로 설정 =====
# 패키지 기준으로 data 디렉토리 구성
PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PKG_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")

# 네이버 로그인 세션(Playwright storage state) 저장 파일
STATE_PATH: str = os.getenv("NCS_STATE_PATH", os.path.join(DATA_DIR, "naver_state.json"))

# 출력 파일 기본 경로(필요 시 scripts에서 덮어씀)
DEFAULT_OUTPUT_CSV: str = os.path.join(OUTPUT_DIR, "naver_cafe_titles.csv")
DEFAULT_OUTPUT_JSON: str = os.path.join(OUTPUT_DIR, "naver_cafe_titles.json")
