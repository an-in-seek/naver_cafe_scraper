# naver_cafe_scraper/utils.py
import os
import re
from typing import Optional, Dict, List

import unicodedata

__all__ = [
    "ensure_dir",
    "build_page_url",
    "load_storage_state",
    "save_storage_state",
    "clean_for_kobert",
]


# -----------------------------------------------------------------------------
# 기본 유틸
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# 텍스트 클리닝 (KoBERT 학습용, 사전/고정 토큰 미사용)
# - URL/이메일/전화번호는 '보존'합니다.
# - 문자군 통계/패턴 기반으로 노이즈 라인 제거
# -----------------------------------------------------------------------------
def _char_stats(s: str) -> Dict[str, float]:
    """문자군 통계: 한글/영문/숫자/공백/기호 비율 등"""
    total = len(s)
    if total == 0:
        return {"total": 0, "ko": 0, "en": 0, "num": 0, "space": 0, "sym": 0}
    ko = sum(1 for ch in s if "\uAC00" <= ch <= "\uD7A3" or "\u3131" <= ch <= "\u318E")
    en = sum(1 for ch in s if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    num = sum(1 for ch in s if ch.isdigit())
    space = s.count(" ")
    sym = total - (ko + en + num + space)
    return {
        "total": total,
        "ko": ko / total,
        "en": en / total,
        "num": num / total,
        "space": space / total,
        "sym": sym / total,
    }


def _looks_like_time_only(s: str) -> bool:
    """시간 형태(HH:MM 등)가 주를 이루고 문자 밀도가 낮은 라인"""
    if not re.search(r"\b\d{1,2}:\d{2}\b", s):
        return False
    stats = _char_stats(s)
    letter = stats["ko"] + stats["en"]
    return (letter < 0.35) and (stats["sym"] + stats["space"] > 0.4)


def _has_long_symbol_runs(s: str) -> bool:
    """===, --- , ___ , ***** , …… 등 긴 기호런 또는 기호-only 단문"""
    if re.search(r"(?:[=\-_*~·•\.]{3,})", s):
        return True
    if len(s) <= 20 and re.fullmatch(r"[\[\]{}()<>/\\|:;^`'\",.!?~=\-_* +]+", s.strip() or ""):
        return True
    return False


def _very_low_linguistic_density(s: str) -> bool:
    """문장성 낮음: 기호 과다/짧은 무의미 토큰 등"""
    stats = _char_stats(s)
    letter = stats["ko"] + stats["en"]
    # 짧고 symbol heavy 이거나 글자 밀도 낮음
    if len(s) <= 50 and (stats["sym"] >= 0.40 or letter < 0.30):
        return True
    # 아주 짧은 단일 토큰
    if len(s.strip()) <= 1:
        return True
    # 공백 거의 없고 글자 밀도 낮은 짧은 라인(코드/ID/잡문자열)
    if stats["space"] < 0.02 and letter < 0.35 and len(s) <= 30:
        return True
    return False


def _is_noisy_line(line: str) -> bool:
    """사전 없이 노이즈 라인 판별"""
    if not line or not line.strip():
        return True
    if _looks_like_time_only(line):
        return True
    if _has_long_symbol_runs(line):
        return True
    if _very_low_linguistic_density(line):
        return True
    return False


def _normalize_visible_text(s: str) -> str:
    """언어 불문 공통 정규화"""
    s = unicodedata.normalize("NFKC", s or "")
    # 제어문자 제거
    s = re.sub(r"[\u0000-\u001F\u007F]", " ", s)
    # ZWSP 제거
    s = s.replace("\u200b", "")
    # 여분 공백 정리
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def clean_for_kobert(text: str) -> str:
    """
    KoBERT 학습용 전처리(사전/고정 토큰 미사용):
    - 문자군 통계/패턴 기반 노이즈 라인 필터
    - 중복/공백 정리(순서 보존)
    """
    if not text:
        return ""

    text = _normalize_visible_text(text)
    raw_lines = [l.strip() for l in re.split(r"\r?\n+", text)]
    cleaned: List[str] = []
    seen = set()

    for line in raw_lines:
        # 기본 공백 정리
        line = re.sub(r"\s{2,}", " ", line).strip()
        if not line:
            continue

        # 노이즈 라인 제거
        if _is_noisy_line(line):
            continue

        # 반복 기호 축약 (~~~~, ---- 등)
        line = re.sub(r"([~\-_=·•])\1{2,}", r"\1\1", line).strip()
        if not line:
            continue

        # 중복 제거 키(문자/숫자/한글만 비교) — 원문 표기는 유지
        key = re.sub(r"[^\w\u3131-\u318E\uAC00-\uD7A3]+", "", line).lower()
        if key and key not in seen:
            seen.add(key)
            cleaned.append(line)

    return "\n".join(cleaned).strip()
