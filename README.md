# Naver Cafe Scraper

네이버 카페 게시글을 **Playwright** 기반으로 크롤링하고,  
이미지 내 텍스트까지 **Tesseract OCR**을 이용해 추출하는 파이썬 프로젝트입니다.  
특히 한글(`kor`), 영어(`eng`) 혼합 문서와 캡처 이미지의 텍스트를 정확히 인식하도록  
**PIL 기반 전처리**(UnsharpMask + Threshold)로 최적화되어 있습니다.

---

## 주요 기능

- **목록 크롤링**: 카페 게시판 글 목록(`title`, `url`, `author`, `date`, `read_count`, `like_count`) 추출
- **상세 크롤링**: 본문 HTML, 텍스트, 외부 링크, 이미지 URL 수집
- **OCR 기능**: 본문 이미지(`img` 태그) 내 텍스트를 자동 인식해 `content_text`에 병합
- **PIL-only 전처리**: Grayscale → UnsharpMask → Threshold(160) → DPI=300 → OCR
- **언어 지원**: 한글+영어(`kor+eng`) 고정
- **출력 포맷**: CSV, JSON 저장

---

## 설치

```bash
git clone https://github.com/yourname/naver_cafe_scraper.git
cd naver_cafe_scraper
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
````

`requirements.txt` 예시:

```txt
playwright>=1.43.0
pandas>=2.0.0
pytesseract
Pillow
```

---

## Tesseract 설치

1. [Tesseract 공식 릴리즈 페이지](https://github.com/UB-Mannheim/tesseract/wiki)에서 OS에 맞는 설치 파일 다운로드
2. 설치 시 `kor.traineddata`, `kor_vert.traineddata`가 포함되도록 언어 데이터 선택
3. 설치 경로 예시:

    * Windows: `C:\Program Files\Tesseract-OCR\tesseract.exe`
    * Mac: `/usr/local/bin/tesseract`

---

## 환경 변수 설정

```powershell
setx NCS_TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
setx NCS_OCR true
```

* `NCS_TESSERACT_CMD`: Tesseract 실행 파일 경로
* `NCS_OCR`: `true` / `false` 로 OCR 실행 여부 제어 (기본값: true)

---

## 크롤링 실행 예시

```bash
python -m scripts.run_crawl \
  --pages 1 \
  --detail \
  --output data/output/naver_cafe_titles.csv \
  --json data/output/naver_cafe_titles.json \
  --progress
```

* `--pages`: 수집할 목록 페이지 수
* `--detail`: 상세 페이지까지 수집
* `--output`: CSV 저장 경로
* `--json`: JSON 저장 경로

---

## OCR 테스트 스크립트

`tests/test_ocr_plus.py`를 이용해 이미지에 대한 다양한 전처리·인식 조합을 자동으로 테스트할 수 있습니다.

```bash
python tests/test_ocr_plus.py \
  --url "이미지_URL" \
  --langs "kor+eng" \
  --psms "6,7,11,3" \
  --oems "1,3" \
  --scales "1.0,1.5,2.0,3.0" \
  --filters "none,sharpen,contrast,unsharp" \
  --thresholds "none,auto,160,190" \
  --dpis "300,420" \
  --topn 5 \
  --tess "C:\Program Files\Tesseract-OCR\tesseract.exe" \
  --save \
  --outdir "data/ocr_debug" \
  --verbose
````

### 주요 인자

| 인자             | 설명                      | 기본값                             |
|----------------|-------------------------|---------------------------------|
| `--url`        | 테스트할 이미지 URL            | (필수)                            |
| `--langs`      | OCR 언어 조합(콤마 구분)        | `kor+eng`                       |
| `--psms`       | Page Segmentation Modes | `6,7,11,3`                      |
| `--oems`       | OCR Engine Modes        | `1,3`                           |
| `--scales`     | 배율                      | `1.0,1.5,2.0,3.0`               |
| `--filters`    | 전처리 필터                  | `none,sharpen,contrast,unsharp` |
| `--thresholds` | 이진화 방식                  | `none,auto,160,190`             |
| `--dpis`       | DPI 값                   | `300,420`                       |
| `--topn`       | 상위 N개 조합 출력             | `5`                             |
| `--tess`       | Tesseract 실행 파일 경로      | 환경변수 `NCS_TESSERACT_CMD`        |
| `--save`       | 전처리 이미지 저장              | 없음                              |
| `--verbose`    | 전처리·인식 과정 로그            | 없음                              |

### 실행 결과 예시

```
[src] size=(1280,720), mode=RGB
[plan] total combos: 288
[001] score=214 lang=kor+eng psm=6 oem=1 sc=1.5 flt=unsharp thr=160 dpi=300
...

================ TOP OCR VARIANTS ================
#153 score=410 lang=kor+eng psm=6 oem=1 sc=3.0 flt=unsharp thr=160 dpi=300
---------------------------------------------------
미국 아마존 판매 1위!! 과학/수학 생활동화! 국내 첫 런칭...

...

================ BEST FULL TEXT ==================
Best: lang=kor+eng psm=6 oem=1 sc=3.0 flt=unsharp thr=160 dpi=300
--------------------------------------------------
미국 아마존 판매 1위!! 과학/수학 생활동화 세트입니다...
==================================================
```

---

## 출력 예시(JSON)

```json
{
  "article_no": "13708359",
  "title": "11번가) 미국 아마존 판매1위 과학/수학 생활동화 69,000원",
  "url": "https://cafe.naver.com/f-e/cafes/29434212/articles/13708359",
  "author": "똘돌잉",
  "date": "2025.08.08. 23:17",
  "read_count": 586,
  "like_count": 9,
  "content_text": "미국 아마존 판매 1위 과학/수학 생활동화 세트예요...\n(이미지 OCR 텍스트 포함)",
  "external_links": [
    "https://www.11st.co.kr/products/8546577618"
  ],
  "images": [
    "https://cafeptthumb-phinf.pstatic.net/...jpg"
  ]
}
```

---

## 라벨링 데이터 생성 예시

(title + content\_text) 조합 후 CSV 저장:

```csv
Sentence,Label
무료 쿠폰 받으세요! 지금 클릭하세요.,광고
지금 가입하면 50% 할인!,광고
이 링크를 통해 이벤트에 참여하세요.,광고
...
```

---

## 주의 사항

* 네이버 카페는 로그인/권한 제한이 있으므로 **Playwright 로그인 세션**이 필요할 수 있습니다.
* OCR 품질은 원본 이미지 해상도와 전처리 효과에 따라 달라집니다.
* 상업적 사용 전 네이버 약관 및 저작권을 반드시 확인하세요.