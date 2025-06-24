import os
import redis
from fastapi import APIRouter, HTTPException, Query
from typing import List
from src.models.faiss_recommenderation_model import FaissRecommendationModel

# 환경 변수로부터 Redis 연결
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Redis 클라이언트 & 추천 모델 초기화
rds = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
recommendation_model = FaissRecommendationModel(rds)

# FastAPI 라우터
router = APIRouter(prefix="/recommend", tags=["Recommendation"])


@router.get("/posts/{user_id}", response_model=List[int], summary="유저 기반 게시글 추천")
def recommend_posts_for_user(
    user_id: int,
    page: int = Query(0, description="페이지 번호"),
    size: int = Query(30, description="페이지당 추천 게시글 수"),
):
    results = recommendation_model.recommend_posts(user_id=user_id, page=page, size=size)
    if not results:
        raise HTTPException(status_code=404, detail="추천 게시글이 없습니다.")
    return results


@router.get("/restaurants/{user_id}", response_model=List[int], summary="유저 기반 식당 추천")
def recommend_restaurants_for_user(
    user_id: int,
    page: int = Query(0, description="페이지 번호"),
    size: int = Query(30, description="페이지당 추천 식당 수"),
):
    results = recommendation_model.recommend_restaurants(user_id=user_id, page=page, size=size)
    if not results:
        raise HTTPException(status_code=404, detail="추천 식당이 없습니다.")
    return results
