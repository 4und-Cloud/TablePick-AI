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
```