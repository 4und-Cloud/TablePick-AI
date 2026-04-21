from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from src.data.cache_initializer import refresh_recommendation_data


if __name__ == "__main__":
    # Batch-style refresh entry point:
    # 1) load from MySQL / Elasticsearch
    # 2) cache source datasets in Redis
    # 3) cache recommender-ready assets in Redis
    refresh_recommendation_data()
