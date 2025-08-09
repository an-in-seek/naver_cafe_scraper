"""
login.py
--------
네이버 카페 크롤링 전 로그인 처리를 담당합니다.
- state_path에 저장된 Playwright storage state를 재사용
- 초기 실행 시 수동 로그인 후 state를 저장하여 이후 자동 로그인
"""

from __future__ import annotations

import os

from playwright.sync_api import Page, BrowserContext

from .utils import ensure_dir


def prompt_login_and_persist(
    page: Page,
    context: BrowserContext,
    state_path: str,
    wait_sec: int = 5,
) -> None:
    """
    네이버 로그인 페이지가 열려있으면 사용자가 직접 로그인할 수 있게 대기 후 세션 저장.

    Parameters
    ----------
    page : playwright.sync_api.Page
        현재 열린 페이지
    context : playwright.sync_api.BrowserContext
        현재 브라우저 컨텍스트
    state_path : str
        로그인 세션 저장 경로(JSON)
    wait_sec : int
        로그인 후 기다릴 시간(초)
    """
    # 로그인 여부를 간단히 판별: "로그인" 버튼이 보이면 로그인 필요
    try:
        login_btn = page.query_selector("a#gnb_login_button, a.link_login, .link_login")
    except Exception:
        login_btn = None

    if login_btn:
        print(f"[login] 네이버 로그인 필요: 브라우저에서 로그인 후 {wait_sec}초 대기...")
        # 로그인 버튼 클릭 시 네이버 로그인 페이지로 이동
        try:
            login_btn.click()
        except Exception:
            pass

        # 사용자가 수동 로그인할 수 있도록 대기
        page.wait_for_timeout(wait_sec * 1000)

        # 로그인 후 쿠키/세션 저장
        ensure_dir(os.path.dirname(state_path))
        context.storage_state(path=state_path)
        print(f"[login] 세션 저장됨: {state_path}")
    else:
        # 이미 로그인된 경우에도 세션 저장
        ensure_dir(os.path.dirname(state_path))
        context.storage_state(path=state_path)
        print(f"[login] 기존 로그인 세션 유지, 저장됨: {state_path}")
