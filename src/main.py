from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.models.prototype_recommendation import RecommendationModel

app = FastAPI(swagger_ui_parameters={"syntaxHighlight": True})

# 추천 모델 인스턴스 생성
recommendation_model = RecommendationModel()

class RestaurantRecommendation(BaseModel):
    restaurant_id: int
    name: str
    address: str
    category: str

class TagPreferences(BaseModel):
    tags: List[str]

@app.get("/")
async def root():
    return {"message": "Restaurant Recommendation API"}

@app.post("/recommendations/{user_id}", response_model=List[RestaurantRecommendation])
async def recommend_by_tags(
    user_id: int,
    preferences: TagPreferences,
    top_n: Optional[int] = 10
):
    """
    태그 리스트를 기반으로 음식점 추천을 제공합니다.
    """
    # 태그 기반 추천
    recommendations = recommendation_model.recommend_by_tags(
        tags=preferences.tags,
        top_n=top_n
    )
    
    if recommendations.empty:
        raise HTTPException(status_code=404, detail="제공된 태그에 맞는 추천을 생성할 수 없습니다.")
    
    # 결과 포맷팅
    result = []
    for idx, row in recommendations.iterrows():
        result.append({
            "restaurant_id": int(idx),
            "name": row["음식점_이름"],
            "address": row["주소"],
            "category": row["카테고리"]
        })
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
