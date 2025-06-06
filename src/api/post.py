import re
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from src.models.post_recommendation import PostRecommendationMLModel
from src.schemas.recommendation import (
    TitleResponse, PostRequest
)
from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration

# kobart-title 모델 및 토크나이저 로드 (최초 1회만)
tokenizer = PreTrainedTokenizerFast.from_pretrained("EbanLee/kobart-title")
model = BartForConditionalGeneration.from_pretrained("EbanLee/kobart-title")

router = APIRouter(prefix="/post", tags=["RestaurantRecommendation"])
recommendation_model = PostRecommendationMLModel()

@router.post("/generate-title", response_model=TitleResponse, summary="게시글 본문으로 제목 생성")
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
    title = re.sub(r'\[.*?\]', '', title).strip()
    return {"title": title}


@router.get("/recommend-for-user/{user_id}", response_model=List[int], summary="유저 데이터 기반 게시글 추천")
def recommend_posts_for_user(
    user_id: int,
    page: int = Query(0, description="페이지 번호"),
    size: int = Query(6, description="페이지당 추천 게시글 수")
):
    """
    user_id로 사용자 태그를 추출, 태그와 게시글 텍스트 임베딩 기반 ML 추천
    """
    print(f"API 호출: user_id={user_id}, page={page}, size={size}")
    results = recommendation_model.recommend_posts(user_id=user_id, page=page, size=size)
    if not results:
        raise HTTPException(status_code=404, detail="추천 게시글이 없습니다.")
    return results