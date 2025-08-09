# naver_cafe_scraper/crawler.py
from __future__ import annotations

import sys
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from .config import (
    BASE_URL,
    MAX_PAGES,
    STATE_PATH,
    HEADLESS,
    WAIT_MS,
    REQUEST_DELAY_SEC,
    DEBUG,
    LOGIN_REQUIRED,
)
from .login import prompt_login_and_persist
from .parser import extract_posts_from_frame, extract_article_detail
from .utils import build_page_url, load_storage_state, save_storage_state

# 프레임 URL에 나타나는 키워드(신스킨/구스킨 호환)
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
        detail_nav_timeout_ms: int = 6000,
        detail_selector_timeout_ms: int = 1500,
        detail_inner_selector_timeout_ms: int = 800,
    ):
        self.base_url = base_url
        self.headless = headless
        self.state_path = state_path
        self.wait_ms = wait_ms
        self.detail_nav_timeout_ms = detail_nav_timeout_ms
        self.detail_selector_timeout_ms = detail_selector_timeout_ms
        self.detail_inner_selector_timeout_ms = detail_inner_selector_timeout_ms

    # ------------------------------------------------------------------
    # Progress helpers
    # ------------------------------------------------------------------
    def _print_progress(self, msg: str, end: str = "\r", flush: bool = True) -> None:
        """간단한 단일 라인 진행상황 출력 (tqdm 무의존)."""
        sys.stdout.write(msg + end)
        if flush:
            sys.stdout.flush()

    # ------------------------------------------------------------------
    # Frame helpers
    # ------------------------------------------------------------------
    def _get_frames(self, page):
        """Playwright Page에서 frames 안전 추출"""
        try:
            fr_attr = getattr(page, "frames", None)
            if callable(fr_attr):
                return fr_attr() or []
            if fr_attr is not None:
                return fr_attr or []
        except Exception:
            pass
        return []

    def _debug_print_frames(self, page) -> None:
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
        1) iframe#cafe_main 우선 시도
        2) 실패 시 URL 키워드 기반 프레임 탐색
        3) 없으면 None (신스킨: 메인 DOM에 바로 렌더링)
        """
        # 1) id/name=cafe_main
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
        return None

    # ------------------------------------------------------------------
    # Detail helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_truthy(base: dict, patch: dict) -> dict:
        """
        빈 값("", [], {}, None)은 덮어쓰지 않고,
        진짜 값이 있는 필드만 base 위에 patch.
        """
        out = dict(base)
        for k, v in patch.items():
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            if isinstance(v, (list, dict)) and not v:
                continue
            out[k] = v
        return out

    def _resolve_url(self, href: str) -> str:
        """상대 경로를 cafe 도메인 기준으로 보정"""
        return urljoin("https://cafe.naver.com", href)

    def _fetch_detail(self, context, link: str) -> Dict[str, object]:
        """새 탭에서 상세 페이지를 열고 충분히 대기 후 파싱"""
        url = self._resolve_url(link)
        page = context.new_page()
        try:
            # 1) 빠른 진입: domcontentloaded 까지만
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=max(self.wait_ms, 30000),
            )

            # 2) 신스킨 핵심 요소를 짧게 대기
            selector = "h3.title_text, .ArticleTitle .title_text, .CafeViewer, .se-viewer"
            try:
                page.wait_for_selector(selector, timeout=self.detail_selector_timeout_ms)
            except Exception:
                page.wait_for_timeout(300)

            # 3) 프레임 전환 필요 시 시도
            frame = self._find_content_frame(page)
            target = frame if frame else page

            # 4) 프레임 내부 재확인(짧게)
            try:
                target.wait_for_selector(
                    selector,
                    timeout=self.detail_inner_selector_timeout_ms,
                )
            except Exception:
                pass

            # 5) 파싱
            return extract_article_detail(target)
        finally:
            page.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def collect(
        self,
        max_pages: int = MAX_PAGES,
        base_url: str | None = None,
        fetch_detail: bool = False,
        per_detail_delay_sec: float = 0.5,
        show_progress: bool = False,  # ← 진척도 출력 스위치
    ) -> List[Dict[str, object]]:
        """
        게시판 목록 수집 + (옵션) 상세 페이지 확장 수집
        - fetch_detail=True 시 본문/이미지/외부링크/작성자/날짜 등 병합
        - show_progress=True 시 콘솔에 진행상황 표시
        """
        start_url = base_url or self.base_url

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                slow_mo=100 if DEBUG and not self.headless else 0,
            )
            context = load_storage_state(browser, self.state_path)
            page = context.new_page()

            all_rows: List[Dict[str, object]] = []
            try:
                for p in range(1, max_pages + 1):
                    if show_progress:
                        self._print_progress(
                            f"[crawl] 페이지 {p}/{max_pages} 로딩 중...", end="\r"
                        )

                    page_url = build_page_url(start_url, p)
                    page.goto(
                        page_url,
                        wait_until="networkidle",
                        timeout=max(self.wait_ms, 30000),
                    )

                    # 첫 페이지에서 로그인 확인/세션 저장
                    if p == 1 and LOGIN_REQUIRED:
                        prompt_login_and_persist(page, context, self.state_path)

                    # 목록이 프레임/신스킨 어디에 있든 타깃 지정
                    frame = self._find_content_frame(page)
                    target = frame if frame else page

                    rows = extract_posts_from_frame(target)
                    if DEBUG:
                        print(f"[page {p}] list items: {len(rows)}")

                    # 페이지 번호 부여
                    for r in rows:
                        r["page"] = p

                    # 상세 파싱이 켜진 경우
                    if fetch_detail and rows:
                        if show_progress:
                            self._print_progress(
                                f"[detail] 페이지 {p} 상세 수집: 0/{len(rows)}", end="\r"
                            )
                        enriched: List[Dict[str, object]] = []
                        for i, r in enumerate(rows, start=1):
                            link = r.get("url") or ""
                            if link:
                                try:
                                    det = self._fetch_detail(context, link)
                                    merged = self._merge_truthy(r, det)
                                    enriched.append(merged)
                                except Exception:
                                    enriched.append(r)
                                if show_progress:
                                    self._print_progress(
                                        f"[detail] 페이지 {p} 상세 수집: {i}/{len(rows)}",
                                        end="\r",
                                    )
                                time.sleep(per_detail_delay_sec)
                            else:
                                enriched.append(r)
                        rows = enriched
                        if show_progress:
                            self._print_progress(
                                f"[detail] 페이지 {p} 상세 수집 완료: {len(rows)}/{len(rows)}",
                                end="\n",
                            )

                    all_rows.extend(rows)
                    time.sleep(REQUEST_DELAY_SEC)

                    if show_progress:
                        self._print_progress(
                            f"[crawl] 페이지 {p}/{max_pages} 완료 (누적 {len(all_rows)}건)",
                            end="\n",
                        )
            finally:
                # 세션 저장 & 정리
                save_storage_state(context, self.state_path)
                context.close()
                browser.close()

            # ✅ 중복 제거 (제목+URL) + (옵션) 본문/이미지 없는 글 제외
            uniq, seen = [], set()
            for r in all_rows:
                if fetch_detail:
                    no_text = not (r.get("content_text") or "").strip()
                    no_images = not r.get("images")
                    if no_text and no_images:
                        continue  # 본문/이미지 모두 없으면 저장 제외

                k = (r.get("title"), r.get("url"))
                if k not in seen:
                    uniq.append(r)
                    seen.add(k)

            if show_progress:
                print(f"[done] 총 {len(uniq)}건 수집 완료")

            return uniq
