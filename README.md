# TablePick AI Recommendation Server

TablePick AI 서버는 **사용자 태그와 행동 로그를 기반으로 개인화 추천을 제공하는 추천 API 서버**입니다.

- 콘텐츠 태그 기반 유사도 추천
- CTR 기반 사용자 반응 반영
- Redis + FAISS 기반 고속 추천 처리

Redis에 추천에 필요한 데이터를 캐싱하고, FAISS를 사용해 태그 벡터 간 유사도를 빠르게 검색합니다.  
추천 순위는 콘텐츠 유사도와 사용자 선호도에 더해, 행동 로그로부터 집계된 CTR 기반 반응 점수를 함께 반영해 계산합니다.

---

## 1. Overview

TablePick AI 서버는 사용자가 좋아할 가능성이 높은 게시글과 음식점을 빠르게 추천하기 위한 서버입니다.

핵심은 다음 두 가지입니다:

- 유사도 기반 후보 생성 (FAISS)
- 사용자 반응 기반 재정렬 (CTR)

이 서버는 추천 API 역할에 집중하며,  
애플리케이션 시작 시 추천 모델을 초기화해 요청 처리 성능을 최적화합니다.

---

## 2. Architecture

```text
Client
  |
  v
FastAPI Router
  |
  v
Recommendation Model (app.state)
  |
  +-- Redis Cache
  |     +-- user preference tags
  |     +-- restaurant tags
  |     +-- post/review tags
  |     +-- CTR values
  |
  +-- FAISS Index
        +-- post vector index
        +-- restaurant vector index

Data Sources
  |
  +-- MySQL (users, restaurants, reviews, tags)
  +-- Elasticsearch (user action logs)
```

현재 활성 추천 경로는 FastAPI lifespan에서 다음 순서로 준비됩니다.

1. MySQL과 Elasticsearch에서 추천에 필요한 데이터를 조회합니다.
2. 조회한 데이터를 Redis에 JSON 형태로 캐싱합니다.
3. Redis 데이터를 읽어 태그 vocabulary를 구성합니다.
4. 게시글과 음식점 태그를 벡터화합니다.
5. FAISS index를 생성합니다.
6. 생성된 추천 모델을 `app.state.recommendation_model`에 저장합니다.

이 구조를 선택한 이유는 다음과 같습니다.

- 요청마다 DB/Elasticsearch를 직접 조회하지 않기 위함
- 캐시 및 메모리 기반으로 빠른 추천 처리
- 추천 모델 초기화 비용 최소화

또한 추천 모델의 생명주기를 FastAPI lifespan에서 관리하여
라우터가 인프라 초기화 책임을 가지지 않도록 역할을 분리했습니다.

---

## 3. Tech Stack

TablePick AI 서버는 **빠른 추천 응답과 확장성을 고려한 구조**로 구성되어 있습니다.

- Python 3.11
- FastAPI
- Uvicorn
- Redis
- FAISS
- Elasticsearch
- MySQL
- SQLAlchemy
- Pandas
- NumPy
- scikit-learn

각 기술의 역할은 다음과 같습니다.

- FastAPI: 추천 API 제공
- Redis: 추천용 데이터와 CTR 값 캐싱
- FAISS: 태그 벡터 기반 유사도 검색
- Elasticsearch: 사용자 행동 로그 조회
- MySQL: 사용자, 게시글, 음식점, 태그 원천 데이터 저장소
- Pandas: 데이터 가공 및 전처리
- NumPy, scikit-learn: 벡터 생성과 정규화 처리

---

## 4. Recommendation Flow

추천 흐름은 다음과 같습니다.

1. 사용자가 추천 API를 호출합니다.
2. 서버는 `app.state.recommendation_model`에서 초기화된 추천 모델을 가져옵니다.
3. 추천 모델은 Redis에서 사용자 선호 태그를 조회합니다.
4. 사용자 태그를 벡터로 변환합니다.
5. FAISS index에서 사용자 벡터와 유사한 게시글 또는 음식점을 검색합니다.
6. 후보 아이템별 CTR 값을 Redis에서 조회합니다.
7. 유사도와 CTR 기반 반응 점수를 조합하여 최종 점수를 계산합니다.
8. 점수가 높은 순서대로 정렬한 뒤 페이지네이션 결과를 반환합니다.

현재 활성 API는 다음과 같습니다.

```text
GET /recommend/posts/{user_id}
GET /recommend/restaurants/{user_id}
```

쿼리 파라미터:

```text
page: 페이지 번호, 기본값 0
size: 페이지당 추천 개수, 기본값 30
```

추천 점수는 다음 요소를 기반으로 구성됩니다

- Similarity: 사용자 선호 태그와 게시글/음식점 태그의 벡터 유사도
- CTR: 사용자의 클릭/조회 행동을 반영한 반응 점수

이 방식은 단순히 태그가 비슷한 항목만 추천하지 않고, 실제 사용자 반응이 좋았던 항목을 함께 우선순위에 반영하기 위해 선택했습니다.

---

## 5. How to Run

### 1. 가상환경 생성

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 만들고 필요한 값을 설정합니다.

```env
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DB=your_database

ES_HOST=http://localhost:9200
```

---

### 4. 필수 인프라 실행

> 서버 시작 시 추천 캐시 초기화를 수행하므로 아래 서비스가 모두 실행 중이어야 합니다.
> 
- MySQL
- Redis
- Elasticsearch

---

### 5. 서버 실행

```bash
uvicorn src.main:app --reload
```

기본 접속 주소:

```text
http://127.0.0.1:8000
```

Swagger 문서:

```text
http://127.0.0.1:8000/docs
```

## 6. Future Improvements

- Redis 데이터 접근을 별도 저장소 계층으로 분리
- 추천 모델과 데이터 로더의 책임 분리 강화
- 추천 점수 가중치 설정값 외부화
- FAISS index 갱신 전략 개선
- CTR 외 추가 행동 신호 (찜, 저장, 재방문 등) 반영
- 추천 품질 평가 지표 도입
- 추천 API 단위 테스트 추가
- 배치 캐싱과 실시간 로그 반영 구조 분리
- 신규 사용자에 대한 fallback 추천 전략 추가
- 추천 결과 다양성(diversity) 개선

