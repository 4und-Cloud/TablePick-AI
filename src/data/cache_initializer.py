import redis
import os
import pandas as pd
from scripts.download.data_loader import DataLoader

class CacheManager:
    def __init__(self):
        self.loader = DataLoader()
        self.redis_client = redis.StrictRedis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )

    def cache_dataframe(self, key, df):
        json_str = df.to_json(orient="records")
        self.redis_client.set(key, json_str)

    def cache_all(self):
        self.cache_dataframe("df:restaurant", self.loader.fetch_restaurant_df())
        self.cache_dataframe("df:review", self.loader.fetch_review_df())
        self.cache_dataframe("df:user_data", self.loader.fetch_user_data_df())
        self.cache_dataframe("df:user_restaurant", self.loader.fetch_user_restaurant_df())
        self.cache_dataframe("df:user_board", self.loader.fetch_user_board_df())
        print("✅ 모든 DF가 Redis에 캐싱되었습니다.")

def cache_dataframe_init():
    manager = CacheManager()
    manager.cache_all()
