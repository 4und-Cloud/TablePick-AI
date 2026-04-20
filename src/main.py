from dotenv import load_dotenv
load_dotenv()
import os
import redis
from fastapi import FastAPI
from contextlib import asynccontextmanager
# from src.api import post
# from src.api import restaurant
from src.api import recommend
from src.data.cache_initializer import cache_dataframe_init
from src.models.faiss_recommenderation_model import FaissRecommendationModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행
    cache_dataframe_init()

    redis_client = redis.StrictRedis(
        host=os.getenv("REDIS_HOST", "127.0.0.1"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )
    app.state.redis_client = redis_client
    app.state.recommendation_model = FaissRecommendationModel(redis_client)

    try:
        yield  # 여기서 서버가 실행됨
    finally:
        redis_client.connection_pool.disconnect()

app = FastAPI(
    title="음식점 추천 API",
    description="다양한 방식의 음식점 추천 서비스를 제공합니다",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "음식점 추천 API에 오신 것을 환영합니다", "version": "1.0.0"}

# app.include_router(post.router)
# app.include_router(restaurant.router)
app.include_router(recommend.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
