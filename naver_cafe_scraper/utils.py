# naver_cafe_scraper/utils.py
import os
import re
from typing import Optional


def ensure_dir(path: str) -> None:
    """지정 경로가 없으면 생성"""
    os.makedirs(path, exist_ok=True)


def build_page_url(base_url: str, page_no: int) -> str:
    """
    네이버 카페 페이지 URL 생성.
    - 기존 page 파라미터를 page_no로 교체
    - 없으면 ? 또는 & 뒤에 추가
    """
    if "page=" in base_url:
        # \g<1>로 그룹 지정 (백참조+숫자 충돌 방지)
        return re.sub(r"(page=)\d+", r"\g<1>" + str(page_no), base_url)
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}page={page_no}"


def load_storage_state(browser, state_path: Optional[str] = None):
    """
    Playwright Browser 인스턴스에서 storage_state를 로드해 새 context를 생성
    """
    kwargs = {}
    if state_path and os.path.exists(state_path):
        kwargs["storage_state"] = state_path
    context = browser.new_context(**kwargs)
    return context


def save_storage_state(context, state_path: Optional[str] = None) -> None:
    """
    Playwright Browser Context의 storage_state를 저장
    """
    if state_path:
        ensure_dir(os.path.dirname(state_path))
        context.storage_state(path=state_path)
