from __future__ import annotations

from typing import List, Dict, Any


def _text(el: Any) -> str:
    """엘리먼트 텍스트 안전 획득"""
    try:
        return (el.inner_text() or "").strip()
    except Exception:
        return ""


def _attr(el: Any, name: str) -> str:
    try:
        v = el.get_attribute(name)
        return v or ""
    except Exception:
        return ""


def _to_int(s: str) -> int:
    try:
        return int(s.replace(",", "").strip())
    except Exception:
        return 0


def extract_posts_from_frame(page_or_frame) -> List[Dict[str, object]]:
    """
    네이버 카페 게시판 목록 파서(신스킨/iframe 공통)
    - 테이블 구조 기준:
        table.article-table > tbody > tr
        글번호:   td.type_articleNumber
        제목/URL: .board-list .inner_list a.article
        말머리:   a.article > span.head (선택)
        작성자:   .ArticleBoardWriterInfo .nickname
        날짜:     td.type_date
        조회수:   td.type_readCount
        좋아요:   td.type_likeCount
    """
    rows: List[Dict[str, object]] = []

    # 목록 대기: 신스킨/iframe 공통으로 tr을 기다림
    try:
        page_or_frame.wait_for_selector("table.article-table tbody tr", timeout=8000)
    except Exception:
        return rows

    trs = page_or_frame.query_selector_all("table.article-table tbody tr")
    for tr in trs:
        try:
            # 글번호
            art_no = _text(tr.query_selector("td.type_articleNumber"))

            # 제목/URL/말머리
            a = tr.query_selector(".board-list .inner_list a.article") or tr.query_selector(
                "a.article"
            )
            if not a:
                # 제목 링크가 없으면 게시글 행이 아닐 수 있음 (공지/광고 영역 등)
                continue
            title = _text(a)
            url = _attr(a, "href")
            head = _text(a.query_selector("span.head")).strip("[] ")

            # 작성자
            author = _text(tr.query_selector(".ArticleBoardWriterInfo .nickname"))

            # 날짜/조회/좋아요
            date = _text(tr.query_selector("td.type_date, td.td_date, .td_normal.type_date"))
            read_count = _to_int(
                _text(tr.query_selector("td.type_readCount, td.td_view, .td_normal.type_readCount"))
            )
            like_count = _to_int(
                _text(tr.query_selector("td.type_likeCount, .td_normal.type_likeCount"))
            )

            row = {
                "article_no": art_no,  # 예: "13709326"
                "head": head,  # 예: "광고" (없을 수 있음)
                "title": title,
                "url": url,
                "author": author,
                "date": date,  # 예: "12:04" 또는 "2025.08.08."
                "read_count": read_count,
                "like_count": like_count,
            }
            rows.append(row)
        except Exception:
            # 행 단위 에러는 스킵
            continue

    return rows
