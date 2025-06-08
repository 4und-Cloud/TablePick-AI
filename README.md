# TablePick-AI
Goorm X Kakao ProFect 에서 진행한 4조 4und Cloud의 프로젝트 TablePick AI팀 입니다.

### 폴더구조
```
data/	        데이터 관련 파일 저장.
├── raw/            # 원본 데이터(raw)
├── processed/      # 전처리된 데이터
├── external/       # 외부에서 수집한 데이터(크롤링 데이터 등)
└── interim/        # 중간 가공 데이터 저장
notebooks/      Jupyter, Colab 등 대화형 노트북 파일 저장. 실험, 분석, 시각화 등 중간 결과 정리.
├── crawling        # 크롤링 관련 노트북
├── EDA/            # 탐색적 데이터 분석(Exploratory Data Analysis) 노트북
├── preprocessing/  # 전처리 관련 노트북
├── modeling/       # 모델링/학습 관련 노트북
└── visualization/  # 시각화 관련 노트북
src/            데이터 처리, 모델 학습, 평가 등 주요 Python 코드 및 스크립트 저장.
├── data/           # 데이터 수집/전처리 관련 코드
├── models/         # 모델 정의/학습 관련 코드
├── utils/          # 유틸리티 함수
└── main.py         # 메인 실행 파일(선택사항)
models/	        학습된 모델 파일(예: .pkl, .pt, .h5 등) 저장.
├── v1/             # 버전 1의 모델 파일들
├── v2/             # 버전 2의 모델 파일들
└── best/           # 최적의 모델 파일
scripts/	    반복 작업, 데이터 다운로드, 전처리 등 자동화 스크립트 저장.
├── download/       # 데이터 다운로드 스크립트
├── preprocess/     # 전처리 스크립트
└── train/          # 학습 스크립트
reports/	    실험 결과, 시각화 자료, 생성된 보고서 등 저장.
├── 20240507/       # 2024년 5월 7일 실험 결과
├── 20240508/       # 2024년 5월 8일 실험 결과
└── final/          # 최종 보고서
configs/	    하이퍼파라미터, 실험 설정 등 구성 파일(YAML, JSON 등) 저장.
├── model1.yaml     # 모델 1 설정
├── model2.yaml     # 모델 2 설정
└── default.yaml    # 기본 설정
docs/	        프로젝트 설명, 문서화 파일, README 등 저장.
├── api/            # API 문서
├── tutorials/      # 튜토리얼/가이드
└── images/         # 문서용 이미지
logs/
├── crawling/       # 크롤링 관련 로그
├── training/       # 모델 학습 관련 로그
└── api/            # API 서비스 관련 로그
```

### 버전
python 3.11.8
rust 1.72.1

### 가상환경
python -m venv venv

call venv.Scripts.activate

pip install -r requirements.txt

### 서버실행
uvicorn src.main:app --reload

### 초기 데이터 정제
ex
python src/data/initial_data_cleaning.py --input "data/raw/서울시 서대문구 일반음식점 인허가 정보.csv" --output "data/interim/sdm_restaurants_cleaned.csv"

### 크롤링 코드 사용법
ex
python src/data/crawler.py --input data/interim/ydp_restaurants_cleaned.csv --output data/external/ydp_crawling_restaurant_data.csv --district 영등포구 --start 5720

### 크롤링 데이터 정제
ex (api-key는 env파일에 설정하셨다면 넣지 않으셔도 됩니다.)
python -m src.data.crawling_data_cleaning --input data/external/gwanak_crawling_restaurant_data.csv --output data/preprocessed/gwanak_restaurants_cleaned_data.csv --gu 영등포구



python -m src.data.crawling_data_cleaning --input data/external/gwanak_crawling_restaurant_data.csv --output data/preprocessed/gwanak_restaurants_cleaned_data.csv