# tests/test_ocr_plus.py
from __future__ import annotations

import argparse
import io
import itertools
import os
import re
import textwrap
from typing import List, Dict

import requests
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

try:
    import pytesseract
except Exception:
    pytesseract = None  # 런타임에서 체크


def set_tesseract_cmd(tess_path: str | None) -> None:
    if pytesseract is None:
        return
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    else:
        env_path = os.environ.get("NCS_TESSERACT_CMD")
        if env_path:
            pytesseract.pytesseract.tesseract_cmd = env_path


def fetch_image(url: str) -> Image.Image:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def to_grayscale(img: Image.Image) -> Image.Image:
    return ImageOps.grayscale(img)


def apply_filter(img: Image.Image, name: str) -> Image.Image:
    if name == "none":
        return img
    if name == "sharpen":
        return img.filter(ImageFilter.SHARPEN)
    if name == "unsharp":
        return img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=180, threshold=3))
    if name == "contrast":
        return ImageEnhance.Contrast(img).enhance(1.6)
    return img


def resize_scale(img: Image.Image, scale: float) -> Image.Image:
    if scale == 1.0:
        return img
    w, h = img.size
    nw, nh = int(w * scale), int(h * scale)
    return img.resize((nw, nh), resample=Image.BICUBIC)


def binarize(img: Image.Image, mode: str | int) -> Image.Image:
    """
    mode:
      - 'auto': 밝기 히스토그램 중앙값 기반 간이 임계(빠름, PIL-only)
      - int   : 명시적 임계값 (0~255)
      - 'none': 이진화 생략
    """
    if mode == "none":
        return img
    gray = ImageOps.grayscale(img)
    if mode == "auto":
        # Otsu 대용 간이판정: 히스토그램 누적 중앙값 활용
        hist = gray.histogram()
        total = sum(hist)
        acc = 0
        thresh = 128
        for i, c in enumerate(hist):
            acc += c
            if acc >= total / 2:
                thresh = i
                break
        t = max(110, min(200, thresh))  # 과도한 극단 방지
    else:
        t = int(mode)
    return gray.point(lambda p: 255 if p >= t else 0, mode="1")


def score_text(s: str) -> int:
    # 간단 스코어: 한글/영문/숫자/공백 가중합 (노이즈 대비)
    if not s:
        return 0
    hangul = len(re.findall(r"[가-힣]", s))
    latin = len(re.findall(r"[A-Za-z]", s))
    digit = len(re.findall(r"\d", s))
    space = s.count(" ")
    return hangul * 5 + latin * 3 + digit * 2 + space


def run_ocr(
    img: Image.Image,
    lang: str,
    psm: int,
    oem: int,
    dpi: int,
    whitelist: str | None = None,
) -> str:
    if pytesseract is None:
        return ""
    config = f"--psm {psm} --oem {oem} -c preserve_interword_spaces=1"
    if whitelist:
        config += f' -c tessedit_char_whitelist="{whitelist}"'
    # DPI 메타는 info에 심어 힌트 제공
    img.info["dpi"] = (dpi, dpi)
    try:
        return pytesseract.image_to_string(img, lang=lang, config=config) or ""
    except Exception:
        return ""


def save_debug(img: Image.Image, outdir: str, name: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{name}.png")
    img.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="테스트할 이미지 URL")
    ap.add_argument("--langs", default="kor+eng,kor,kor_vert",
                    help="콤마로 분리된 언어 조합 (기본: kor+eng,kor,kor_vert)")
    ap.add_argument("--psms", default="6,7,11,3",
                    help="콤마로 분리된 PSM 목록 (기본: 6,7,11,3)")
    ap.add_argument("--oems", default="1,3",
                    help="콤마로 분리된 OEM 목록 (기본: 1,3)")
    ap.add_argument("--scales", default="1.0,1.5,2.0,3.0",
                    help="콤마로 분리된 스케일 목록 (기본: 1.0,1.5,2.0,3.0)")
    ap.add_argument("--filters", default="none,sharpen,contrast,unsharp",
                    help="콤마로 분리된 필터 목록 (기본: none,sharpen,contrast,unsharp)")
    ap.add_argument("--thresholds", default="none,auto,160,190",
                    help="콤마로 분리된 이진화 목록 (기본: none,auto,160,190)")
    ap.add_argument("--dpis", default="300,420",
                    help="콤마로 분리된 DPI 목록 (기본: 300,420)")
    ap.add_argument("--topn", type=int, default=5, help="상위 결과 출력 개수")
    ap.add_argument("--tess", default=None, help="tesseract 실행 파일 경로")
    ap.add_argument("--save", action="store_true", help="전처리 이미지 저장")
    ap.add_argument("--outdir", default="data/ocr_debug", help="세이브 디렉토리")
    ap.add_argument("--verbose", action="store_true", help="자세한 로그")
    args = ap.parse_args()

    if pytesseract is None:
        print("[err] pytesseract 미설치. `pip install pytesseract pillow` 필요")
        return

    set_tesseract_cmd(args.tess)

    base = fetch_image(args.url)
    print(f"[src] size={base.size}, mode={base.mode}")
    base_g = to_grayscale(base)

    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    psms = [int(x) for x in args.psms.split(",")]
    oems = [int(x) for x in args.oems.split(",")]
    scales = [float(x) for x in args.scales.split(",")]
    filters = [x.strip() for x in args.filters.split(",")]
    thresholds = [x.strip() if x.strip() in ("none", "auto") else int(x) for x in args.thresholds.split(",")]
    dpis = [int(x) for x in args.dpis.split(",")]

    # 조합 생성
    combos = list(itertools.product(scales, filters, thresholds, dpis, langs, psms, oems))
    print(f"[plan] total combos: {len(combos)}")

    results: List[Dict] = []

    for idx, (sc, flt, thr, dpi, lang, psm, oem) in enumerate(combos, start=1):
        # 전처리
        img = resize_scale(base_g, sc)
        img = apply_filter(img, flt)
        img = binarize(img, thr)

        if args.save and idx <= 60:  # 저장 과다 방지
            save_debug(img, args.outdir, f"{idx:03d}_sc{sc}_{flt}_thr{thr}_dpi{dpi}")

        # OCR
        text = run_ocr(img, lang=lang, psm=psm, oem=oem, dpi=dpi)
        s = score_text(text)
        results.append(
            dict(
                idx=idx, score=s, text=text,
                scale=sc, filter=flt, thr=thr, dpi=dpi, lang=lang, psm=psm, oem=oem
            )
        )
        if args.verbose:
            print(f"[{idx:03d}] score={s:4d} lang={lang} psm={psm} oem={oem} sc={sc} flt={flt} thr={thr} dpi={dpi}")

    # 상위 N 출력
    results.sort(key=lambda x: x["score"], reverse=True)
    print("\n================ TOP OCR VARIANTS ================")
    for r in results[: args.topn]:
        header = f"#{r['idx']} score={r['score']} lang={r['lang']} psm={r['psm']} oem={r['oem']} sc={r['scale']} flt={r['filter']} thr={r['thr']} dpi={r['dpi']}"
        print(header)
        print("-" * len(header))
        sample = r["text"].strip() or "(no text)"
        print(textwrap.shorten(sample.replace("\n", " ")[:1000], width=300, placeholder=" …"))
        print()
    print("==================================================")

    # 베스트 원문 전체 출력
    if results and (results[0]["text"].strip()):
        best = results[0]
        print("\n================ BEST FULL TEXT ==================")
        print(
            f"Best: lang={best['lang']} psm={best['psm']} oem={best['oem']} sc={best['scale']} flt={best['filter']} thr={best['thr']} dpi={best['dpi']}")
        print("--------------------------------------------------")
        print(best["text"])
        print("==================================================")
    else:
        print("\n[hint] 유의미한 텍스트가 적습니다. 다음을 시도해 보세요:")
        print("- --scales 를 2.0,3.0,4.0 으로 더 키우기")
        print("- --thresholds 에 130,150,170 등 추가")
        print("- --psms 5,6,7,11,12 다양화")
        print("- 이미지에 텍스트 대비가 낮다면 --filters contrast, unsharp 조합")


if __name__ == "__main__":
    main()
