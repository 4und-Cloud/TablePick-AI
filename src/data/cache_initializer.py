import json
import os

import numpy as np
import redis
from sklearn.preprocessing import normalize

from scripts.download.data_loader import DataLoader


class CacheManager:
    def __init__(self):
        self.loader = DataLoader()
        self.redis_client = redis.StrictRedis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
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
        print("Cached source datasets in Redis.")

    def _load_cached_rows(self, key):
        json_data = self.redis_client.get(key)
        if not json_data:
            return []
        return json.loads(json_data)

    def _build_tag_vocab(self):
        tags = set()
        for key in ("df:user_data", "df:review", "df:restaurant"):
            for row in self._load_cached_rows(key):
                for tag_obj in row.get("tags", []):
                    tags.add(tag_obj["tag_id"])
        return sorted(tags)

    @staticmethod
    def _to_vector(tag_vocab, tags):
        tag_set = set(tags)
        return np.array([1 if tag in tag_set else 0 for tag in tag_vocab], dtype=np.float32)

    def _build_index_payload(self, redis_key, id_key, tag_vocab):
        rows = self._load_cached_rows(redis_key)
        item_ids = []
        item_vectors = []

        for row in rows:
            tag_ids = [tag["tag_id"] for tag in row.get("tags", [])]
            item_ids.append(row[id_key])
            item_vectors.append(self._to_vector(tag_vocab, tag_ids))

        if not item_vectors:
            return [], []

        normalized_vectors = normalize(np.array(item_vectors, dtype=np.float32), axis=1)
        return item_ids, normalized_vectors.tolist()

    def cache_recommendation_assets(self):
        # Prepare FAISS-ready assets during the refresh step so the API only loads them at startup.
        tag_vocab = self._build_tag_vocab()
        post_ids, post_vectors = self._build_index_payload("df:review", "board_id", tag_vocab)
        restaurant_ids, restaurant_vectors = self._build_index_payload(
            "df:restaurant", "restaurant_id", tag_vocab
        )

        self.redis_client.set("rec:tag_vocab", json.dumps(tag_vocab))
        self.redis_client.set("rec:post_ids", json.dumps(post_ids))
        self.redis_client.set("rec:post_vectors", json.dumps(post_vectors))
        self.redis_client.set("rec:restaurant_ids", json.dumps(restaurant_ids))
        self.redis_client.set("rec:restaurant_vectors", json.dumps(restaurant_vectors))
        print("Cached recommendation-ready assets in Redis.")

    def refresh_all(self):
        self.cache_all()
        self.cache_recommendation_assets()


def refresh_recommendation_data():
    manager = CacheManager()
    manager.refresh_all()


def cache_dataframe_init():
    # Backward-compatible alias for the previous startup-oriented function name.
    refresh_recommendation_data()
