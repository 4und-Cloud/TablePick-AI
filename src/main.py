from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.models.prototype_recommendation import RecommendationModel
from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration

# kobart-title 모델 및 토크나이저 로드 (최초 1회만)
tokenizer = PreTrainedTokenizerFast.from_pretrained("EbanLee/kobart-title")
model = BartForConditionalGeneration.from_pretrained("EbanLee/kobart-title")

app = FastAPI(title="음식점 추천 API", description="다양한 방식의 음식점 추천 서비스를 제공합니다", version="1.0.0")

# 추천 모델 인스턴스 생성
recommendation_model = RecommendationModel()

class PostRequest(BaseModel):
    content: str

class TitleResponse(BaseModel):
    title: str

class RestaurantRecommendation(BaseModel):
    restaurant_id: int
    restaurant_name: str
    address: str
    category: str

class TagPreferences(BaseModel):
    tags: List[str]

class LocationData(BaseModel):
    latitude: float
    longitude: float
    max_distance_km: Optional[float] = 5.0

@app.get("/")
async def root():
    return {"message": "음식점 추천 API에 오신 것을 환영합니다", "version": "1.0.0"}

@app.post("/generate-title", response_model=TitleResponse, summary="게시글 본문으로 제목 생성")
async def generate_title(request: PostRequest):
    if not request.content or request.content.strip() == "":
        raise HTTPException(status_code=400, detail="본문이 비어 있습니다.")
    # 토크나이즈 및 제목 생성
    input_ids = tokenizer.encode(request.content, return_tensors="pt", max_length=1024, truncation=True)
    summary_ids = model.generate(
        input_ids=input_ids,
        bos_token_id=model.config.bos_token_id,
        eos_token_id=model.config.eos_token_id,
        length_penalty=1.0,
        max_length=40,
        min_length=3,
        num_beams=6,
        repetition_penalty=1.5,
    )
    title = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return {"title": title}

@app.post("/recommendations/tags", response_model=List[RestaurantRecommendation])
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

@app.get("/recommendations/restaurant/{restaurant_id}", response_model=List[RestaurantRecommendation])
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

@app.post("/recommendations/preferences", response_model=List[RestaurantRecommendation])
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

@app.get("/recommendations/user/{user_id}", response_model=List[RestaurantRecommendation])
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

@app.get("/recommendations/user/{user_id}/advanced", response_model=List[RestaurantRecommendation])
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

@app.get("/recommendations/user/{user_id}/collaborative", response_model=List[RestaurantRecommendation])
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

@app.get("/recommendations/user/{user_id}/hybrid", response_model=List[RestaurantRecommendation])
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
