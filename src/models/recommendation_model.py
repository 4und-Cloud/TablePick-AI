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
                tags.update(row["tag_id"])

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
                return row["tag_id"]
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

        # 1) 후보군 필터링 : 태그가 겹치는 게시물만 추림
        filtered_items = [
            row for row in review_data
            if user_tag_set.intersection(row["tag_id"])
        ]
        if not filtered_items:
            return []

        # 2) 아이템 태그 벡터 미리 계산
        item_vectors = []
        item_ids = []
        for row in filtered_items:
            vec = [1 if tag in row["tag_id"] else 0 for tag in self.tag_vocab]
            item_vectors.append(vec)
            item_ids.append(row["board_id"])
        item_vectors = np.array(item_vectors)

        # 3) 사용자 태그 벡터
        user_vec = self._to_vector(user_tags).reshape(1, -1)

        # 4) 코사인 유사도 batch 계산
        sims = cosine_similarity(user_vec, item_vectors)[0]

        # 5) CTR 키 리스트 생성 & bulk 조회 (필요한 게시물만)
        ctr_keys = [f"{user_id}:board:{board_id}:ctr" for board_id in item_ids]
        ctr_values = self.get_ctr_bulk(ctr_keys)

        max_ctr = max(ctr_values) if ctr_values else 0

        # 6) 점수 계산
        scores = []
        for board_id, sim, ctr in zip(item_ids, sims, ctr_values):
            ctr_score = math.log(1 + ctr)
            norm_ctr = ctr_score / math.log(1 + max_ctr) if max_ctr > 0 else 0
            total_score = sim + norm_ctr
            if total_score > 0:
                scores.append((board_id, total_score))

        # 7) 점수 내림차순 정렬 및 페이징
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

        # 1) 후보군 필터링: 사용자 태그와 겹치는 식당만
        filtered_items = [
            row for row in restaurant_data
            if user_tag_set.intersection(row["tag_id"])
        ]
        if not filtered_items:
            return []

        # 2) 아이템 태그 벡터 미리 계산
        item_vectors = []
        item_ids = []
        for row in filtered_items:
            vec = [1 if tag in row["tag_id"] else 0 for tag in self.tag_vocab]
            item_vectors.append(vec)
            item_ids.append(row["restaurant_id"])
        item_vectors = np.array(item_vectors)

        # 3) 사용자 태그 벡터
        user_vec = self._to_vector(user_tags).reshape(1, -1)

        # 4) 코사인 유사도 계산
        sims = cosine_similarity(user_vec, item_vectors)[0]

        # 5) CTR 키 생성 & bulk 조회
        ctr_keys = [f"{user_id}:restaurant:{restaurant_id}:ctr" for restaurant_id in item_ids]
        ctr_values = self.get_ctr_bulk(ctr_keys)

        # 6) max_ctr 계산
        max_ctr = max(ctr_values) if ctr_values else 0

        # 7) 점수 계산
        scores = []
        for restaurant_id, sim, ctr in zip(item_ids, sims, ctr_values):
            ctr_score = math.log(1 + ctr)
            norm_ctr = ctr_score / math.log(1 + max_ctr) if max_ctr > 0 else 0
            total_score = sim + norm_ctr
            if total_score > 0:
                scores.append((restaurant_id, total_score))

        # 8) 정렬 및 페이징
        scores.sort(key=lambda x: x[1], reverse=True)
        recommended = [restaurant_id for restaurant_id, _ in scores]

        start = page * size
        end = start + size
        return recommended[start:end]


