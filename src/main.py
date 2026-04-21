from contextlib import asynccontextmanager
import os

import redis
from dotenv import load_dotenv
from fastapi import FastAPI

from src.api import recommend
from src.models.faiss_recommenderation_model import FaissRecommendationModel


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = redis.StrictRedis(
        host=os.getenv("REDIS_HOST", "127.0.0.1"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True,
    )
    app.state.redis_client = redis_client
    # Startup only loads recommendation assets that were prepared by the refresh script.
    app.state.recommendation_model = FaissRecommendationModel(redis_client)

    try:
        yield
    finally:
        redis_client.connection_pool.disconnect()


app = FastAPI(
    title="음식점 추천 API",
    description="다양한 방식의 음식점 추천 서비스를 제공합니다",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "음식점 추천 API에 오신 것을 환영합니다", "version": "1.0.0"}


app.include_router(recommend.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
