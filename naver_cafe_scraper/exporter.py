from __future__ import annotations

import json
import os
from typing import List, Dict, Iterable, Optional

import pandas as pd

from .config import OUTPUT_DIR, DEFAULT_OUTPUT_CSV, DEFAULT_OUTPUT_JSON
from .utils import ensure_dir


def _as_dataframe(rows: Iterable[Dict], fields: Optional[List[str]] = None) -> pd.DataFrame:
    df = pd.DataFrame(list(rows))
    if fields:
        # 존재하는 컬럼만 유지하여 순서 정렬
        keep = [c for c in fields if c in df.columns]
        df = df[keep]
    return df


def save_csv(
    rows: Iterable[Dict],
    path: Optional[str] = None,
    fields: Optional[List[str]] = None,
    include_index: bool = False,
    encoding: str = "utf-8-sig",  # Excel 호환 위해 BOM 포함
) -> str:
    """
    rows를 CSV로 저장합니다.
    - fields: 컬럼 순서를 지정하고 싶을 때 사용 (없는 컬럼은 무시)
    - include_index: 인덱스 저장 여부
    """
    ensure_dir(OUTPUT_DIR)
    out_path = path or DEFAULT_OUTPUT_CSV
    df = _as_dataframe(rows, fields)
    df.to_csv(out_path, index=include_index, encoding=encoding)
    return out_path


def save_json(
    rows: Iterable[Dict],
    path: Optional[str] = None,
    fields: Optional[List[str]] = None,
    ensure_ascii: bool = False,
    indent: int = 2,
) -> str:
    """
    rows를 JSON(lines 아님)으로 저장합니다.
    - fields: 컬럼/키 순서를 제한하고 싶을 때 사용 (없는 키는 무시)
    """
    ensure_dir(OUTPUT_DIR)
    out_path = path or DEFAULT_OUTPUT_JSON
    if fields:
        # dict 정렬 적용
        filtered = []
        for r in rows:
            filtered.append({k: r.get(k) for k in fields if k in r})
        payload = filtered
    else:
        payload = list(rows)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=ensure_ascii, indent=indent)
    return out_path


# (선택) Parquet 저장이 필요하면 사용하세요.
def save_parquet(
    rows: Iterable[Dict],
    path: Optional[str] = None,
    fields: Optional[List[str]] = None,
    engine: Optional[str] = None,  # "pyarrow" 또는 "fastparquet"
) -> str:
    """
    rows를 Parquet로 저장합니다. engine이 None이면 pandas 기본 우선 순위를 따릅니다.
    """
    ensure_dir(OUTPUT_DIR)
    out_path = path or os.path.join(OUTPUT_DIR, "naver_cafe_titles.parquet")
    df = _as_dataframe(rows, fields)
    df.to_parquet(out_path, index=False, engine=engine)
    return out_path
