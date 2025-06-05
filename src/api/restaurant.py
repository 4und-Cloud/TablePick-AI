from fastapi import APIRouter, HTTPException, Query
from src.models.prototype_recommendation import RecommendationModel
from src.schemas.recommendation import (
    TagPreferences, LocationData, RestaurantRecommendation
)
from typing import List, Optional

router = APIRouter(prefix="/restaurants", tags=["RestaurantRecommendation"])
recommendation_model = RecommendationModel()

@router.post("/recommend-by-tags", response_model=List[RestaurantRecommendation], summary="태그 리스트 기반 음식점 추천")
async def recommend_by_tags(
    preferences: TagPreferences,
    top_n: int = Query(10, description="반환할 추천 음식점 수")
):
    """
    태그 리스트를 기반으로 음식점 추천을 제공합니다.
    """
    recommendations = recommendation_model.recommend_by_tags(
        tags=preferences.tags,
        top_n=top_n
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail="제공된 태그에 맞는 추천을 생성할 수 없습니다.")
    
    result = []
    for idx, row in recommendations.iterrows():
        result.append(
            RestaurantRecommendation(
                restaurant_id=int(idx),
                restaurant_name=row["음식점_이름"],
                address=row["주소"],
                category=row["카테고리"]
            )
        )
    
    return result

@router.get("/recommend/{restaurant_id}", response_model=List[RestaurantRecommendation], summary="유사한 음식점 추천")
async def recommend_similar_restaurants(
    restaurant_id: int,
    top_n: int = Query(10, description="반환할 추천 음식점 수")
):
    """
    특정 음식점과 유사한 음식점들을 추천합니다.
    """
    recommendations = recommendation_model.recommend_by_restaurant(
        restaurant_idx=restaurant_id,
        top_n=top_n
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail=f"ID {restaurant_id}에 해당하는 음식점을 찾을 수 없거나 추천을 생성할 수 없습니다.")
    
    result = []
    for idx, row in recommendations.iterrows():
        result.append(
            RestaurantRecommendation(
                restaurant_id=int(idx),
                restaurant_name=row["음식점_이름"],
                address=row["주소"],
                category=row["카테고리"]
            )
        )
    
    return result

@router.post("/recommend-by-preferences", response_model=List[RestaurantRecommendation], summary="사용자 선호도, 위치 기반 추천")
async def recommend_by_preferences(
    preferences: TagPreferences,
    location: Optional[LocationData] = None,
    top_n: int = Query(10, description="반환할 추천 음식점 수")
):
    """
    사용자 선호도와 위치 정보를 기반으로 음식점을 추천합니다.
    """
    user_lat = location.latitude if location else None
    user_lon = location.longitude if location else None
    max_distance = location.max_distance_km if location else None
    
    recommendations = recommendation_model.recommend_by_preferences(
        preferences=preferences.tags,
        user_lat=user_lat,
        user_lon=user_lon,
        top_n=top_n,
        max_distance_km=max_distance
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail="제공된 선호도에 맞는 추천을 생성할 수 없습니다.")
    
    result = []
    for idx, row in recommendations.iterrows():
        result.append(
            RestaurantRecommendation(
                restaurant_id=int(idx),
                restaurant_name=row["음식점_이름"],
                address=row["주소"],
                category=row["카테고리"]
            )
        )
    
    return result

@router.get("/recommend-for-user/{user_id}", response_model=List[RestaurantRecommendation], summary="사용자 기반 음식점 추천")
async def recommend_for_user(
    user_id: int,
    top_n: int = Query(5, description="반환할 추천 음식점 수")
):
    """
    사용자 ID를 기반으로 음식점을 추천합니다.
    """
    recommendations = recommendation_model.recommend_by_user_id(
        user_id=user_id,
        top_n=top_n
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail=f"사용자 ID {user_id}에 대한 추천을 생성할 수 없습니다.")
    
    result = []
    for _, row in recommendations.iterrows():
        result.append(
            RestaurantRecommendation(
                restaurant_id=int(row["restaurant_id"]),
                restaurant_name=row["음식점_이름"],
                address=row["주소"],
                category=row["카테고리"]
            )
        )
    
    return result

@router.get("/recommend-for-user/{user_id}/advanced", response_model=List[RestaurantRecommendation], summary="사용자 태그와 방문 기록 기반 음식점 추천")
async def recommend_for_user_advanced(
    user_id: int,
    top_n: int = Query(5, description="반환할 추천 음식점 수")
):
    """
    사용자 태그와 방문 기록을 모두 고려한 고급 추천 시스템입니다.
    """
    recommendations = recommendation_model.recommend_by_user_id_advanced(
        user_id=user_id,
        top_n=top_n
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail=f"사용자 ID {user_id}에 대한 고급 추천을 생성할 수 없습니다.")
    
    result = []
    for _, row in recommendations.iterrows():
        result.append(
            RestaurantRecommendation(
                restaurant_id=int(row["restaurant_id"]),
                restaurant_name=row["음식점_이름"],
                address=row["주소"],
                category=row["카테고리"]
            )
        )
    
    return result

@router.get("/recommend-for-user/{user_id}/collaborative", response_model=List[RestaurantRecommendation], summary="협업 필터링 기반 음식점 추천")
async def recommend_collaborative_filtering(
    user_id: int,
    top_n: int = Query(10, description="반환할 추천 음식점 수")
):
    """
    협업 필터링 기반으로 음식점을 추천합니다.
    """
    recommendations = recommendation_model.recommend_collaborative(
        user_id=user_id,
        top_n=top_n
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail=f"사용자 ID {user_id}에 대한 협업 필터링 추천을 생성할 수 없습니다.")
    
    result = []
    for _, row in recommendations.iterrows():
        result.append(
            RestaurantRecommendation(
                restaurant_id=int(row["restaurant_id"]),
                restaurant_name=row["음식점_이름"],
                address=row["주소"],
                category=row["카테고리"]
            )
        )
    
    return result

@router.get("/recommend-for-user/{user_id}/hybrid", response_model=List[RestaurantRecommendation], summary="하이브리드 음식점 추천")
async def recommend_hybrid(
    user_id: int,
    top_n: int = Query(5, description="반환할 추천 음식점 수")
):
    """
    콘텐츠 기반 필터링과 협업 필터링을 결합한 하이브리드 추천을 제공합니다.
    """
    recommendations = recommendation_model.recommend_hybrid(
        user_id=user_id,
        top_n=top_n
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail=f"사용자 ID {user_id}에 대한 하이브리드 추천을 생성할 수 없습니다.")
    
    result = []
    for _, row in recommendations.iterrows():
        result.append(
            RestaurantRecommendation(
                restaurant_id=int(row["restaurant_id"]),
                restaurant_name=row["음식점_이름"],
                address=row["주소"],
                category=row["카테고리"]
            )
        )
    
    return result

