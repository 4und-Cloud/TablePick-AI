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
        # Redis MGET (bulk get) 사용 가정
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

        # 1) 아이템 태그 벡터를 미리 계산
        item_vectors = []
        item_ids = []
        for row in review_data:
            vec = [1 if tag in row["tag_id"] else 0 for tag in self.tag_vocab]
            item_vectors.append(vec)
            item_ids.append(row["board_id"])
        item_vectors = np.array(item_vectors)

        # 2) 사용자 태그 벡터
        user_vec = self._to_vector(user_tags).reshape(1, -1)

        # 3) 코사인 유사도 한 번에 계산
        sims = cosine_similarity(user_vec, item_vectors)[0]

        # 4) CTR 키 리스트 만들고 MGET으로 한 번에 가져오기
        ctr_keys = [f"{user_id}:board:{board_id}:ctr" for board_id in item_ids]
        ctr_values = self.get_ctr_bulk(ctr_keys)

        # 5) max_ctr 계산
        max_ctr = max(ctr_values) if ctr_values else 0

        # 6) 점수 계산
        scores = []
        for board_id, sim, ctr in zip(item_ids, sims, ctr_values):
            ctr_score = math.log(1 + ctr)
            norm_ctr = ctr_score / math.log(1 + max_ctr) if max_ctr > 0 else 0
            total_score = sim + norm_ctr
            if total_score > 0:
                scores.append((board_id, total_score))

        # 7) 점수 내림차순 정렬
        scores.sort(key=lambda x: x[1], reverse=True)
        recommended = [board_id for board_id, _ in scores]

        # 8) 페이징 처리
        start = page * size
        end = start + size
        return recommended[start:end]
