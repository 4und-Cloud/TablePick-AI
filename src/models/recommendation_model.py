import math
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class RecommendationModel:
    def __init__(self, rds):
        self.rds = rds
        self.tag_vocab = self._load_tag_vocab()

    def _load_tag_vocab(self):
        user_data_json = self.rds.get("df:user_data")
        review_json = self.rds.get("df:review")
        restaurant_json = self.rds.get("df:restaurant")

        tags = set()
        for data in [user_data_json, review_json, restaurant_json]:
            if not data:
                continue
            for row in json.loads(data):
                tag_ids = [tag["tag_id"] for tag in row.get("tags", [])]
                tags.update(tag_ids)

        return sorted(tags)

    def _to_vector(self, tags):
        return np.array([1 if tag in tags else 0 for tag in self.tag_vocab])

    def get_user_tags(self, user_id: int):
        user_data_json = self.rds.get("df:user_data")
        if not user_data_json:
            return None
        user_data = json.loads(user_data_json)
        for row in user_data:
            if row["member_id"] == user_id:
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

    def recommend_posts(self, user_id: int, page: int = 0, size: int = 6):
        user_tags = self.get_user_tags(user_id)
        if not user_tags:
            return []

        review_json = self.rds.get("df:review")
        if not review_json:
            return []
        review_data = json.loads(review_json)

        user_tag_set = set(user_tags)

        filtered_items = []
        item_vectors = []
        item_ids = []

        for row in review_data:
            tag_ids = [tag["tag_id"] for tag in row.get("tags", [])]
            if user_tag_set.intersection(tag_ids):
                filtered_items.append(row)
                item_ids.append(row["board_id"])
                vec = [1 if tag in tag_ids else 0 for tag in self.tag_vocab]
                item_vectors.append(vec)

        if not filtered_items:
            return []

        item_vectors = np.array(item_vectors)
        user_vec = self._to_vector(user_tags).reshape(1, -1)

        sims = cosine_similarity(user_vec, item_vectors)[0]

        ctr_keys = [f"{user_id}:board:{board_id}:ctr" for board_id in item_ids]
        ctr_values = self.get_ctr_bulk(ctr_keys)

        max_ctr = max(ctr_values) if ctr_values else 0

        scores = []
        for board_id, sim, ctr in zip(item_ids, sims, ctr_values):
            ctr_score = math.log(1 + ctr)
            norm_ctr = ctr_score / math.log(1 + max_ctr) if max_ctr > 0 else 0
            total_score = sim + norm_ctr
            if total_score > 0:
                scores.append((board_id, total_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        recommended = [board_id for board_id, _ in scores]

        start = page * size
        end = start + size
        return recommended[start:end]

    def recommend_restaurants(self, user_id: int, page: int = 0, size: int = 6):
        user_tags = self.get_user_tags(user_id)
        if not user_tags:
            return []

        restaurant_json = self.rds.get("df:restaurant")
        if not restaurant_json:
            return []
        restaurant_data = json.loads(restaurant_json)

        user_tag_set = set(user_tags)

        filtered_items = []
        item_vectors = []
        item_ids = []

        for row in restaurant_data:
            tag_ids = [tag["tag_id"] for tag in row.get("tags", [])]
            if user_tag_set.intersection(tag_ids):
                filtered_items.append(row)
                item_ids.append(row["restaurant_id"])
                vec = [1 if tag in tag_ids else 0 for tag in self.tag_vocab]
                item_vectors.append(vec)

        if not filtered_items:
            return []

        item_vectors = np.array(item_vectors)
        user_vec = self._to_vector(user_tags).reshape(1, -1)

        sims = cosine_similarity(user_vec, item_vectors)[0]

        ctr_keys = [f"{user_id}:restaurant:{restaurant_id}:ctr" for restaurant_id in item_ids]
        ctr_values = self.get_ctr_bulk(ctr_keys)

        max_ctr = max(ctr_values) if ctr_values else 0

        scores = []
        for restaurant_id, sim, ctr in zip(item_ids, sims, ctr_values):
            ctr_score = math.log(1 + ctr)
            norm_ctr = ctr_score / math.log(1 + max_ctr) if max_ctr > 0 else 0
            total_score = sim + norm_ctr
            if total_score > 0:
                scores.append((restaurant_id, total_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        recommended = [restaurant_id for restaurant_id, _ in scores]

        start = page * size
        end = start + size
        return recommended[start:end]
