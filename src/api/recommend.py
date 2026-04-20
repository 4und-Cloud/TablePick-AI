from fastapi import APIRouter, HTTPException, Query, Request
from typing import List

# FastAPI 라우터
router = APIRouter(prefix="/recommend", tags=["Recommendation"])


def get_recommendation_model(request: Request):
    return request.app.state.recommendation_model


@router.get("/posts/{user_id}", response_model=List[int], summary="유저 기반 게시글 추천")
def recommend_posts_for_user(
    request: Request,
    user_id: int,
    page: int = Query(0, description="페이지 번호"),
    size: int = Query(30, description="페이지당 추천 게시글 수"),
):
    recommendation_model = get_recommendation_model(request)
    results = recommendation_model.recommend_posts(user_id=user_id, page=page, size=size)
    if not results:
        raise HTTPException(status_code=404, detail="추천 게시글이 없습니다.")
    return results


@router.get("/restaurants/{user_id}", response_model=List[int], summary="유저 기반 식당 추천")
def recommend_restaurants_for_user(
    request: Request,
    user_id: int,
    page: int = Query(0, description="페이지 번호"),
    size: int = Query(30, description="페이지당 추천 식당 수"),
):
    recommendation_model = get_recommendation_model(request)
    results = recommendation_model.recommend_restaurants(user_id=user_id, page=page, size=size)
    if not results:
        raise HTTPException(status_code=404, detail="추천 식당이 없습니다.")
    return results
