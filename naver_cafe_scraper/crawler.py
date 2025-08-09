from __future__ import annotations

import time
from typing import List, Dict, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from .config import (
    BASE_URL,
    MAX_PAGES,
    STATE_PATH,
    HEADLESS,
    WAIT_MS,
    REQUEST_DELAY_SEC,
    DEBUG,
)
from .login import prompt_login_and_persist
from .parser import extract_posts_from_frame
from .utils import build_page_url, load_storage_state, save_storage_state

CONTENT_URL_KEYWORDS = (
    "ArticleList",
    "Menu",
    "/menus/",
    "ArticleList.nhn",
    "MenuArticles.nhn",
)


class CafeCrawler:
    def __init__(
        self,
        base_url: str = BASE_URL,
        headless: bool = HEADLESS,
        state_path: str = STATE_PATH,
        wait_ms: int = WAIT_MS,
    ):
        self.base_url = base_url
        self.headless = headless
        self.state_path = state_path
        self.wait_ms = wait_ms

    # --- 내부 유틸: 프레임 안전 접근 -------------------------------------------------
    def _get_frames(self, page):
        """Playwright Page.frames가 리스트/메서드인 경우 모두 안전하게 반환."""
        try:
            fr_attr = getattr(page, "frames", None)
            if callable(fr_attr):  # 일부 테스트 더블에서 frames() 메서드
                return fr_attr() or []
            if fr_attr is not None:  # Playwright 실제 객체에선 리스트 속성
                return fr_attr or []
        except Exception:
            pass
        return []

    def _debug_print_frames(self, page):
        if not DEBUG:
            return
        print("[debug] frames:")
        for i, f in enumerate(self._get_frames(page)):
            try:
                name = getattr(f, "name", None)
                name = name() if callable(name) else name
                url = getattr(f, "url", "")
                url = url() if callable(url) else url
                print(f"  - #{i} name={name!r} url={url}")
            except Exception:
                pass

    def _find_content_frame(self, page) -> Optional[object]:
        """
        1) iframe#cafe_main 시도
        2) 프레임 URL 키워드 매칭
        3) 프레임이 없으면 None(= 신스킨)
        """
        # 1) cafe_main 대기 & 접근 (page.frame이 없을 수도 있으니 방어)
        try:
            page.wait_for_selector("iframe#cafe_main", timeout=self.wait_ms)
            frame_fn = getattr(page, "frame", None)
            if callable(frame_fn):
                fr = frame_fn(name="cafe_main")
                if fr:
                    return fr
        except PWTimeout:
            pass
        except Exception:
            pass

        # 2) URL 키워드 매칭
        self._debug_print_frames(page)
        for f in self._get_frames(page):
            try:
                url = getattr(f, "url", "")
                url = url() if callable(url) else url
                if any(k in (url or "") for k in CONTENT_URL_KEYWORDS):
                    return f
            except Exception:
                continue

        # 3) 신스킨일 가능성 (본문이 page에 직접 렌더링)
        return None

    # --- public: 수집 ---------------------------------------------------------------
    def collect(
        self, max_pages: int = MAX_PAGES, base_url: str | None = None
    ) -> List[Dict[str, str]]:
        start_url = base_url or self.base_url

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                slow_mo=100 if DEBUG and not self.headless else 0,
            )
            context = load_storage_state(browser, self.state_path)
            page = context.new_page()

            all_rows: List[Dict[str, str]] = []
            try:
                for p in range(1, max_pages + 1):
                    page_url = build_page_url(start_url, p)
                    page.goto(
                        page_url,
                        wait_until="networkidle",
                        timeout=max(self.wait_ms, 30000),
                    )

                    if p == 1:
                        # 최초 1회 수동 로그인 기회 제공(로그인 필요 없으면 즉시 저장)
                        prompt_login_and_persist(page, context, self.state_path, wait_sec=20)

                    frame = self._find_content_frame(page)
                    target = frame if frame else page  # 신스킨이면 page 자체 파싱

                    rows = extract_posts_from_frame(target)
                    if DEBUG:
                        print(f"[page {p}] 수집 {len(rows)}건")

                    for r in rows:
                        r["page"] = p
                    all_rows.extend(rows)

                    time.sleep(REQUEST_DELAY_SEC)
            finally:
                # 세션 저장
                save_storage_state(context, self.state_path)
                context.close()
                browser.close()

            # 중복 제거 (제목+URL)
            uniq, seen = [], set()
            for r in all_rows:
                k = (r.get("title"), r.get("url"))
                if k not in seen:
                    uniq.append(r)
                    seen.add(k)
            return uniq
