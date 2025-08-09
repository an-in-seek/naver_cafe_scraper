# Naver Cafe Scraper

이 프로젝트는 **Playwright**를 이용해 네이버 카페 게시글을 크롤링하고,
본문 이미지에 포함된 텍스트까지 **Tesseract OCR**로 추출하는 Python 기반 도구입니다.
특히 한글(`kor`)과 영어(`eng`)가 혼합된 문서나 캡처 이미지에서도 높은 인식률을 유지하도록,
**PIL 기반 전처리**(UnsharpMask + Threshold)를 적용해 OCR 성능을 최적화했습니다.

---

## 주요 기능

* **목록 크롤링**
    * 카페 게시판 글 목록을 수집: `title`, `url`, `author`, `date`, `read_count`, `like_count`
* **상세 크롤링**
    * 게시글 본문 HTML과 텍스트, 외부 링크, 이미지 URL을 추출
* **OCR 처리**
    * 본문에 포함된 이미지(`<img>` 태그)의 텍스트를 자동 인식하고, 결과를 `content_text`에 병합
* **고정밀 전처리(PIL-only)**
    * Grayscale 변환 → UnsharpMask → Threshold(160) → DPI=300 설정 → OCR 수행
* **언어 지원**
    * 한글+영어(`kor+eng`) 혼합 인식 지원
* **다양한 출력 포맷**
    * CSV, JSON 파일로 저장 가능

---

## 설치

### 1. 필수 패키지 설치

아래는 이 프로젝트 실행에 필요한 주요 Python 패키지 예시입니다.
`requirements.txt` 파일에 추가해 두면 한 번에 설치할 수 있습니다.

```txt
playwright>=1.43.0   # 네이버 카페 크롤링용 브라우저 자동화
pandas>=2.0.0        # 크롤링 결과 CSV/데이터 처리
pytesseract          # 이미지 내 텍스트 추출(OCR)
Pillow               # 이미지 전처리(Grayscale, 필터, Threshold 등)
```

### 2. 패키지 설치 명령어

```bash
pip install -r requirements.txt
```

### 3. Playwright 브라우저 드라이버 설치

Playwright를 처음 설치했다면, 브라우저 드라이버도 함께 설치해야 합니다.

```bash
playwright install
```

> 💡 **팁**: 가상환경(venv)을 사용하면 프로젝트별 패키지 버전을 독립적으로 관리할 수 있어 충돌을 방지할 수 있습니다.

---

## Tesseract 설치

1. [Tesseract 공식 릴리즈 페이지](https://github.com/UB-Mannheim/tesseract/wiki)에서 **운영체제(OS)에 맞는 설치 파일**을 다운로드합니다.
2. 설치 시 한국어(`kor.traineddata`)와 **세로쓰기(`kor_vert.traineddata`)** 언어 데이터가 포함되도록 선택합니다.
3. 설치 완료 후 실행 파일 경로 예시:

    * **Windows**:

      ```
      C:\Program Files\Tesseract-OCR\tesseract.exe
      ```
    * **macOS**:

      ```
      /usr/local/bin/tesseract
      ```

> 💡 참고: macOS에서는 `brew install tesseract`로 설치할 수 있으며, 한국어 데이터는 `brew install tesseract-lang` 명령어로 추가할 수 있습니다.

---

## 환경 변수 설정

Tesseract 경로와 OCR 실행 여부를 환경 변수로 설정합니다.

```powershell
setx NCS_TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
setx NCS_OCR true
```

| 환경 변수               | 설명                                        |
|---------------------|-------------------------------------------|
| `NCS_TESSERACT_CMD` | Tesseract 실행 파일 경로                        |
| `NCS_OCR`           | OCR 실행 여부 (`true` 또는 `false`, 기본값 `true`) |

> 📌 Windows PowerShell에서 위 명령어를 실행하면 환경 변수가 등록됩니다.
> 새 터미널에서 적용되도록 PowerShell을 재시작하는 것을 권장합니다.

---

## 크롤링 실행 예시

아래 명령어는 네이버 카페 게시글을 **목록 페이지 1쪽부터 상세 내용까지** 크롤링하고, 결과를 **CSV와 JSON** 두 가지 포맷으로 저장합니다.

```bash
python -m scripts.run_crawl \
  --pages 1 \
  --detail \
  --output data/output/naver_cafe_titles.csv \
  --json data/output/naver_cafe_titles.json \
  --progress
```

### 옵션 설명

| 옵션           | 설명                                         |
|--------------|--------------------------------------------|
| `--pages`    | 수집할 목록 페이지 수. 예: `--pages 3` → 목록 3쪽까지 크롤링 |
| `--detail`   | 목록뿐만 아니라 각 게시글의 **상세 페이지 내용**까지 함께 수집      |
| `--output`   | 크롤링 결과를 저장할 CSV 파일 경로                      |
| `--json`     | 크롤링 결과를 저장할 JSON 파일 경로                     |
| `--progress` | 진행 상황을 터미널에 실시간 표시                         |

### 실행 후 생성되는 데이터 예시

* **CSV 파일** → 엑셀, Google Sheets에서 바로 열어볼 수 있는 표 형식
* **JSON 파일** → 다른 스크립트나 프로그램에서 가공·분석하기 좋은 구조화 데이터

> 💡 **팁**:
> * `--pages` 값을 늘리면 더 많은 데이터를 수집할 수 있지만, 그만큼 크롤링 시간이 길어집니다.
> * `--detail` 옵션 없이 실행하면 목록 데이터만 빠르게 수집할 수 있습니다.
> * CSV와 JSON을 동시에 저장해두면, 분석과 재처리를 유연하게 할 수 있습니다.

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

## 라벨링 데이터 생성 가이드

KoBERT 모델 학습을 위해서는 **문장과 라벨**이 매칭된 데이터셋이 필요합니다.
아래 예시는 JSON 원본 데이터를 광고/정상 여부 라벨이 포함된 CSV 형태로 변환하는 방법을 보여줍니다.

---

### 1) 데이터 준비

* **입력 데이터(JSON)**: 게시글 제목과 본문, 기타 메타데이터가 포함된 JSON 파일
* **출력 데이터(CSV)**: KoBERT 학습 포맷(`Sentence`, `Label` 컬럼)

---

### 2) 변환 스크립트 실행 예시

```bash
python -m scripts.make_dataset ^
  --input data/output/naver_cafe_titles.json ^     # 입력 JSON 파일 경로
  --output data/output/dataset_ad.csv ^            # 출력 CSV 파일 경로
  --label "광고" ^                                  # 지정할 라벨 값
  --sep " " ^                                       # 제목과 본문을 연결할 구분자
  --require-body                                    # 본문이 없는 데이터는 제외
```

#### 주요 옵션 설명

| 옵션               | 설명                                 |
|------------------|------------------------------------|
| `--input`        | 변환할 원본 JSON 데이터 경로                 |
| `--output`       | 변환된 CSV 저장 경로                      |
| `--label`        | 해당 데이터에 부여할 라벨명(예: `"광고"`, `"정상"`) |
| `--sep`          | 제목과 본문을 연결할 때 사용할 구분자              |
| `--require-body` | 본문이 없는 데이터는 변환 대상에서 제외             |

---

### 3) 출력 CSV 예시

```csv
Sentence,Label
무료 쿠폰 받으세요! 지금 클릭하세요.,광고
지금 가입하면 50% 할인!,광고
이 링크를 통해 이벤트에 참여하세요.,광고
이 제품 진짜 좋아요. 써보세요.,광고
```

> 📌 **주의**:
>
> * `Sentence` 컬럼은 KoBERT의 입력 텍스트
> * `Label` 컬럼은 해당 문장의 분류 값
> * CSV는 UTF-8 인코딩 권장

---

### 4) 라벨링 전략 팁

* 광고 라벨(`광고`)과 정상 라벨(`정상`)을 **균형 있게 수집**하면 모델 학습 성능이 좋아집니다.
* 광고 데이터는 **쿠폰, 할인, 구매 유도, 특정 링크 포함** 문구 등을 우선적으로 라벨링합니다.
* 정상 데이터는 **광고 성격이 없는 일반 대화, 정보 공유 글**로 채웁니다.
* 데이터 품질이 곧 모델 품질이므로, **중복·불필요 데이터는 사전에 제거**하세요.

---

### 5) 학습 시 주의사항

* CSV 파일 경로와 인코딩을 KoBERT 학습 스크립트에서 정확히 지정해야 합니다.
* 라벨명이 다국어/한글일 경우, 학습 코드에서 `label2id` 매핑이 동일하게 적용되도록 설정하세요.
* 데이터 증강 기법(문장 순서 변경, 동의어 치환 등)을 적절히 활용하면 데이터 부족 문제를 완화할 수 있습니다.

---

## 주의 사항

* 네이버 카페는 로그인/권한 제한이 있으므로 **Playwright 로그인 세션**이 필요할 수 있습니다.
* OCR 품질은 원본 이미지 해상도와 전처리 효과에 따라 달라집니다.
* 상업적 사용 전 네이버 약관 및 저작권을 반드시 확인하세요.