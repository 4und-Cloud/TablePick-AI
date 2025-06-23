from fastapi import FastAPI
from contextlib import asynccontextmanager
# from src.api import post
# from src.api import restaurant
from src.api import recommend
from src.data.cache_initializer import cache_dataframe_init
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행
    cache_dataframe_init()

    yield  # 여기서 서버가 실행됨

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
