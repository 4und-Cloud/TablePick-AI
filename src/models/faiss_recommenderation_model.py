import json
import math

import faiss
import numpy as np
from sklearn.preprocessing import normalize


class FaissRecommendationModel:
    def __init__(self, rds):
        self.rds = rds
        self.tag_vocab = self._load_json("rec:tag_vocab", [])
        self.post_ids = self._load_json("rec:post_ids", [])
        self.restaurant_ids = self._load_json("rec:restaurant_ids", [])
        self.post_index = self._load_index("rec:post_vectors")
        self.restaurant_index = self._load_index("rec:restaurant_vectors")

    def _load_json(self, key, default):
        json_data = self.rds.get(key)
        if not json_data:
            return default
        return json.loads(json_data)

    def _to_vector(self, tags):
        tag_set = set(tags)
        return np.array([1 if tag in tag_set else 0 for tag in self.tag_vocab], dtype=np.float32)

    def _load_index(self, vector_key):
        if not self.tag_vocab:
            return None

        vectors = self._load_json(vector_key, [])
        if not vectors:
            return None

        item_vectors = np.array(vectors, dtype=np.float32)
        index = faiss.IndexFlatIP(len(self.tag_vocab))
        index.add(item_vectors)
        return index

    def get_user_tags(self, user_id: int):
        user_data_json = self.rds.get("df:user_data")
        if not user_data_json:
            return None
        user_data = json.loads(user_data_json)
        for row in user_data:
            if row.get("member_id") == user_id:
                return [tag["tag_id"] for tag in row.get("tags", [])]
        return None

    def get_ctr_bulk(self, keys):
        vals = self.rds.mget(keys)
        ctrs = []
        for val in vals:
            try:
                ctrs.append(float(val) if val else 0.0)
            except Exception:
                ctrs.append(0.0)
        return ctrs

    def _recommend_from_index(self, user_tags, index, item_ids, ctr_prefix, user_id, page, size):
        if not index or not item_ids:
            return []

        user_vec = normalize(self._to_vector(user_tags).reshape(1, -1), axis=1)

        top_k = min(100, len(item_ids))
        sims, indices = index.search(user_vec, top_k)

        selected_ids = [item_ids[i] for i in indices[0]]
        ctr_keys = [f"{user_id}:{ctr_prefix}:{item_id}:ctr" for item_id in selected_ids]
        ctr_values = self.get_ctr_bulk(ctr_keys)

        max_ctr = max(ctr_values) if ctr_values else 0

        scores = []
        for item_id, sim, ctr in zip(selected_ids, sims[0], ctr_values):
            ctr_score = math.log(1 + ctr)
            norm_ctr = ctr_score / math.log(1 + max_ctr) if max_ctr > 0 else 0
            total_score = sim + norm_ctr
            if total_score > 0:
                scores.append((item_id, total_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        recommended = [item_id for item_id, _ in scores]

        start = page * size
        end = start + size
        return recommended[start:end]

    def recommend_posts(self, user_id: int, page: int = 0, size: int = 6):
        user_tags = self.get_user_tags(user_id)
        if not user_tags:
            return []
        return self._recommend_from_index(
            user_tags,
            self.post_index,
            self.post_ids,
            ctr_prefix="board",
            user_id=user_id,
            page=page,
            size=size,
        )

    def recommend_restaurants(self, user_id: int, page: int = 0, size: int = 6):
        user_tags = self.get_user_tags(user_id)
        if not user_tags:
            return []
        return self._recommend_from_index(
            user_tags,
            self.restaurant_index,
            self.restaurant_ids,
            ctr_prefix="restaurant",
            user_id=user_id,
            page=page,
            size=size,
        )
