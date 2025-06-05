import uvicorn
from fastapi import FastAPI
from src.api import restaurant, post
from src.utils.export_utils import run_export_scripts

# run_export_scripts()

app = FastAPI(title="음식점 추천 API", description="다양한 방식의 음식점 추천 서비스를 제공합니다", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "음식점 추천 API에 오신 것을 환영합니다", "version": "1.0.0"}

app.include_router(restaurant.router)
app.include_router(post.router)

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
