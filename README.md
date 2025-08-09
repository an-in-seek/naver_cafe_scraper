# Naver Cafe Scraper

네이버 카페 게시판의 글 제목과 URL을 크롤링하여 CSV로 저장하는 파이썬 프로젝트입니다.  
Playwright를 사용하여 로그인 세션 유지 및 페이지 탐색을 수행합니다.

---

## 📂 프로젝트 구조

```

naver\_cafe\_scraper/
├── data/ # 상태/출력 데이터 저장
│ └── output/ # 크롤링 결과 저장 폴더
│ └── naver\_state.json # 로그인 세션 상태
│
├── naver\_cafe\_scraper/ # 패키지 코드
│ ├── config.py # 설정값 관리
│ ├── crawler.py # 크롤링 로직
│ ├── exporter.py # CSV/JSON 저장 로직
│ ├── login.py # 로그인 처리
│ ├── parser.py # HTML 파싱
│ ├── utils.py # 유틸 함수
│ └── **init**.py
│
├── scripts/ # 실행 스크립트
│ ├── run\_crawl.py # 크롤링 실행
│ └── run\_export.py # 결과 저장 실행
│
├── tests/ # 테스트 코드
│ ├── test\_crawler.py
│ ├── test\_crawler\_flow\.py
│ ├── test\_exporter.py
│ ├── test\_login.py
│ ├── test\_parser.py
│ ├── test\_utils.py
│ └── conftest.py
│
├── pyproject.toml # Black, Flake8 설정
├── requirements.txt # 필수 패키지
├── requirements-dev.txt # 개발/테스트 패키지
└── README.md

````

---

## 📦 설치 방법

```bash
# 저장소 클론
git clone https://github.com/your-username/naver_cafe_scraper.git
cd naver_cafe_scraper

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # (Windows) .venv\Scripts\activate

# 필수 패키지 설치
pip install -r requirements.txt

# 개발/테스트 환경 패키지 설치
pip install -r requirements-dev.txt
````

---

## 🚀 사용 방법

### 1. 크롤링 실행

```bash
# 기본 실행
python -m scripts.run_crawl --pages 1 --output data/output/naver_cafe_titles.csv
```

* `--pages`: 크롤링할 페이지 수
* `--output`: 저장할 CSV 파일 경로

### 2. 저장/후처리 실행

```bash
python -m scripts.run_export --input data/output/naver_cafe_titles.csv --format json
```

* `--input`: 입력 파일 경로
* `--format`: 저장 형식 (`csv`, `json`)

---

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest -q

# 커버리지 측정
pytest -q --cov=naver_cafe_scraper

# 특정 테스트 실행
pytest tests/test_crawler.py
```

---

## 🎯 코드 스타일 검사

```bash
# Flake8 문법 검사
flake8 naver_cafe_scraper

# Black 코드 포맷 검사
black --check .
# Black 자동 포맷
black .
```

---

## 📌 주요 기술 스택

* **Python 3.11**
* **Playwright**: 웹 자동화 및 크롤링
* **Pandas**: 데이터 저장/가공
* **Pytest**: 테스트
* **Black / Flake8**: 코드 스타일 관리

---

## ⚠️ 주의사항

* 네이버 카페 크롤링 시 이용 약관과 로봇 배제 표준을 반드시 준수하세요.
* 로그인 정보와 세션 파일(`naver_state.json`)은 외부에 노출되지 않도록 주의하세요.

```