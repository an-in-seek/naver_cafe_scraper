# naver_cafe_scraper/parser.py
from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple, Optional

from .utils import clean_for_kobert

# -----------------------------------------------------------------------------
# Config (일원화)
# -----------------------------------------------------------------------------
# 고정값(필요시 여기서만 바꾸면 됨)
_OCR_ENABLED_DEFAULT = True  # 상세 파싱 시 OCR 수행 기본 on
_OCR_LANG = "kor+eng"  # 언어
_OCR_PSM = 6  # page segmentation mode
_OCR_OEM = 1  # engine mode
_OCR_SCALE = 1.0  # 배율(1.0 = 원본)
_OCR_FILTER = "unsharp"  # "unsharp" 고정
_OCR_THRESH = 160  # 이진화 임계값(0~255)
_OCR_DPI = 300  # DPI 메타데이터 힌트

# Tesseract 실행 파일(있으면 사용)
_TESSERACT_CMD = os.getenv(
    "NCS_TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
# 환경변수로 OCR 껐다 켰다 하고 싶으면 사용 (없으면 기본 True)
_OCR_ENABLED_ENV = os.getenv("NCS_OCR", "").lower() in {"1", "true", "yes", "y"}


# -----------------------------------------------------------------------------
# 공통 유틸
# -----------------------------------------------------------------------------
def _text(el) -> str:
    """Playwright ElementHandle/Locator에서 텍스트 안전 추출"""
    if not el:
        return ""
    try:
        return el.inner_text().strip()
    except Exception:
        try:
            t = el.text_content()
            return t.strip() if t else ""
        except Exception:
            return ""


def _int_from_text(s: str) -> int:
    m = re.search(r"\d[\d,]*", s or "")
    return int(m.group(0).replace(",", "")) if m else 0


def _dedup_keep_order(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


# -----------------------------------------------------------------------------
# 목록 파서
# -----------------------------------------------------------------------------
def extract_posts_from_frame(target) -> List[Dict[str, object]]:
    """
    게시판 목록에서 글 목록 추출
    - 신스킨(table.article-table) 우선, 없으면 구스킨(a.article, a.tit 등) 대응
    반환: [{article_no,title,url,author,date,read_count,like_count}, ...]
    """
    rows: List[Dict[str, object]] = []

    # 1) 신스킨: table.article-table
    try:
        table = target.query_selector("table.article-table")
        if table:
            trs = table.query_selector_all("tbody > tr")
            for tr in trs:
                no = _text(tr.query_selector("td.type_articleNumber")) or ""
                a = tr.query_selector("a.article")
                title = _text(a)
                url = a.get_attribute("href") if a else ""
                author = _text(tr.query_selector(".ArticleBoardWriterInfo .nickname"))
                date = _text(tr.query_selector("td.type_date"))
                rc = _int_from_text(_text(tr.query_selector("td.type_readCount")))
                lc = _int_from_text(_text(tr.query_selector("td.type_likeCount")))
                if title and url:
                    rows.append(
                        {
                            "article_no": no,
                            "title": title,
                            "url": url,
                            "author": author,
                            "date": date,
                            "read_count": rc,
                            "like_count": lc,
                        }
                    )
            if rows:
                return rows
    except Exception:
        pass

    # 2) 구스킨(보수적)
    try:
        links = target.query_selector_all("a.article, a.tit")
        for a in links:
            title = _text(a)
            url = a.get_attribute("href") or ""
            if title and url:
                rows.append({"title": title, "url": url})
    except Exception:
        pass

    return rows


# -----------------------------------------------------------------------------
# 상세 파서(내부 헬퍼)
# -----------------------------------------------------------------------------
def _find_content_root(target):
    """본문 루트 노드(CafeViewer 혹은 se-viewer)"""
    try:
        return target.query_selector("div.CafeViewer") or target.query_selector(
            "div.se-viewer"
        )
    except Exception:
        return None


def _extract_basic_fields(target, data: Dict[str, object]) -> None:
    # 제목
    try:
        ttl = target.query_selector("h3.title_text") or target.query_selector(
            ".ArticleTitle .title_text, .TitleText"
        )
        data["title"] = _text(ttl)
    except Exception:
        pass
    # 작성자
    try:
        nick = target.query_selector(".WriterInfo .nickname, .nick_name, .nickname")
        data["author"] = _text(nick)
    except Exception:
        pass
    # 날짜
    try:
        dt = target.query_selector(".article_info .date, .date")
        data["date"] = _text(dt)
    except Exception:
        pass
    # 조회/좋아요
    try:
        rc_el = target.query_selector(".article_info .count, .count, .read")
        data["read_count"] = _int_from_text(_text(rc_el))
    except Exception:
        pass
    try:
        like_el = target.query_selector(".u_likeit_list_btn .u_cnt, .like_no .u_cnt")
        data["like_count"] = _int_from_text(_text(like_el))
    except Exception:
        pass


def _extract_body_text_and_html(content_root) -> Tuple[str, str]:
    """본문 텍스트와 HTML"""
    content_text, content_html = "", ""
    if not content_root:
        return content_text, content_html
    try:
        content_html = content_root.inner_html() or ""
    except Exception:
        content_html = ""
    try:
        # 문단성 요소 위주로 수집
        paras = content_root.query_selector_all("p, div.se-text-paragraph, li")
        texts = [(_text(p) or "").strip() for p in paras]
        texts = [t for t in texts if t]
        content_text = "\n".join(texts)
    except Exception:
        content_text = ""
    return content_text, content_html


def _extract_external_links_and_images(content_root) -> Tuple[List[str], List[str]]:
    links, imgs = [], []
    if not content_root:
        return links, imgs
    try:
        for a in content_root.query_selector_all("a, a.se-link"):
            href = a.get_attribute("href")
            if href and href.startswith(("http://", "https://")):
                links.append(href)
    except Exception:
        pass
    try:
        for img in content_root.query_selector_all(
            "img, .se-oglink-thumbnail-resource"
        ):
            src = img.get_attribute("src")
            if src:
                imgs.append(src)
    except Exception:
        pass
    return _dedup_keep_order(links), _dedup_keep_order(imgs)


def _extract_image_side_texts(content_root) -> List[str]:
    """이미지의 alt/캡션/주변 텍스트 추출 (OCR 제외)"""
    out: List[str] = []
    if not content_root:
        return out
    try:
        for img in content_root.query_selector_all("img"):
            alt = img.get_attribute("alt") or ""
            if alt.strip():
                out.append(alt.strip())
    except Exception:
        pass
    try:
        for cap_sel in [
            ".se-caption",
            ".se-imageCaption",
            ".se-oglink-title",
            ".se-oglink-summary",
            ".se-module-image figcaption",
        ]:
            for el in content_root.query_selector_all(cap_sel):
                t = _text(el)
                if t:
                    out.append(t)
    except Exception:
        pass
    return _dedup_keep_order(out)


def _pil_unsharp_threshold(im, thr: int) -> "Image.Image":
    """PIL만 사용: 그레이스케일 → 언샤프 → 이진화(thr)."""
    from PIL import ImageFilter

    g = im.convert("L")
    if _OCR_FILTER == "unsharp":
        # 기본 반경/강도/임계값은 보수적 세팅
        g = g.filter(ImageFilter.UnsharpMask(radius=1.5, percent=180, threshold=3))
    # 임계값 이진화
    bw = g.point(lambda p: 255 if p > thr else 0, mode="1")
    return bw.convert("L")  # tesseract가 L/RGB에 더 안정적


def _apply_scale(im, scale: float) -> "Image.Image":
    if not scale or abs(scale - 1.0) < 1e-6:
        return im
    w, h = im.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return im.resize((nw, nh))


def _ocr_on_images(content_root) -> List[str]:
    """
    이미지 요소를 스크린샷 캡처해 OCR (PIL-only 전처리).
    - pillow, pytesseract가 없으면 빈 리스트
    - Tesseract 설치 경로가 있으면 사용
    """
    try:
        from PIL import Image  # noqa: F401
        import pytesseract
    except Exception:
        return []

    # tesseract 경로 설정(있을 경우)
    try:
        if _TESSERACT_CMD and os.path.exists(_TESSERACT_CMD):
            pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    except Exception:
        pass

    if not content_root:
        return []

    try:
        imgs = content_root.query_selector_all("img")
    except Exception:
        imgs = []

    results: List[str] = []
    for img in imgs:
        try:
            # DOM 요소 스크린샷 → bytes
            png_bytes = img.screenshot()
            if not png_bytes:
                continue

            from io import BytesIO
            from PIL import Image

            im = Image.open(BytesIO(png_bytes))

            # 스케일 적용 (요청값: 1.0 → 사실상 원본)
            im = _apply_scale(im, _OCR_SCALE)

            # 언샤프 + 임계값 이진화(160)
            im = _pil_unsharp_threshold(im, _OCR_THRESH)

            # Tesseract 인자 구성
            config = f"--psm {_OCR_PSM} --oem {_OCR_OEM}"
            # DPI 힌트: PNG 메타에 DPI 넣어서 전달 (없어도 동작)
            buf = BytesIO()
            im.save(buf, format="PNG", dpi=(_OCR_DPI, _OCR_DPI))
            buf.seek(0)
            im2 = Image.open(buf)

            txt = pytesseract.image_to_string(im2, lang=_OCR_LANG, config=config) or ""
            txt = txt.strip()
            if txt:
                results.append(txt)
        except Exception:
            continue

    return _dedup_keep_order(results)


# -----------------------------------------------------------------------------
# 상세 파서(공개 API)
# -----------------------------------------------------------------------------
def extract_article_detail(
    target,
    *,
    ocr: Optional[bool] = None,
) -> Dict[str, object]:
    """
    게시글 상세 페이지에서 주요 정보 추출
    - title, author, date, read_count, like_count
    - content_text(본문+alt/캡션+OCR), content_html
    - external_links, images

    ocr:
      None -> 환경변수(NCS_OCR) 있으면 따르고, 없으면 기본 True
      True/False -> 강제 지정
    """
    data: Dict[str, object] = {
        "title": "",
        "author": "",
        "date": "",
        "read_count": 0,
        "like_count": 0,
        "content_text": "",
        "content_html": "",
        "external_links": [],
        "images": [],
    }

    _extract_basic_fields(target, data)

    content_root = _find_content_root(target)
    body_text, content_html = _extract_body_text_and_html(content_root)
    links, images = _extract_external_links_and_images(content_root)
    side_texts = _extract_image_side_texts(content_root)

    # OCR 여부 결정(인자 > 환경변수 > 기본값 True)
    if ocr is None:
        ocr_enabled = _OCR_ENABLED_ENV if os.getenv("NCS_OCR") else _OCR_ENABLED_DEFAULT
    else:
        ocr_enabled = bool(ocr)

    ocr_texts: List[str] = _ocr_on_images(content_root) if ocr_enabled else []

    # content_text: 본문 + (alt/캡션) + (OCR)
    merged_parts = [body_text] + side_texts + ocr_texts
    merged_text = "\n".join([t for t in merged_parts if t]).strip()

    # KoBERT 전처리 적용
    cleaned_text = clean_for_kobert(merged_text if merged_text else body_text)

    data["content_text"] = cleaned_text if cleaned_text else (merged_text or body_text)
    data["content_html"] = content_html
    data["external_links"] = links
    data["images"] = images

    return data
