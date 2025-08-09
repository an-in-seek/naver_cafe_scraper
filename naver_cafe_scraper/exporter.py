# naver_cafe_scraper/exporter.py
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Dict, List, Any


def _ensure_parent(path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)


def _gather_all_keys(rows: Iterable[Dict[str, Any]]) -> List[str]:
    keys: set[str] = set()
    for r in rows:
        keys.update(r.keys())
    return sorted(keys)


def _preferred_order(all_keys: List[str]) -> List[str]:
    # 상세 + 목록 통합 컬럼 순서 (없는 건 뒤로 밀림)
    preferred = [
        "page",
        "article_no",
        "title",
        "url",
        "author",
        "date",
        "read_count",
        "like_count",
        "content_text",
        "content_html",
        "external_links",
        "images",
    ]
    tail = [k for k in all_keys if k not in preferred]
    return preferred + tail


def _serialize(v: Any) -> Any:
    # 리스트/딕셔너리는 CSV에서 보기가 좋도록 JSON 문자열로
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v


def save_csv(rows: List[Dict[str, Any]], path: str | Path) -> None:
    _ensure_parent(path)
    if not rows:
        # 빈 결과라도 헤더는 남기고 싶으면 여기서 기본 헤더 정의 가능
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["title", "url"])
        return

    all_keys = _gather_all_keys(rows)
    fieldnames = _preferred_order(all_keys)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: _serialize(r.get(k, "")) for k in fieldnames})


def save_json(rows: List[Dict[str, Any]], path: str | Path, indent: int = 2) -> None:
    _ensure_parent(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=indent)
