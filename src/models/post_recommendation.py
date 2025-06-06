import pandas as pd
import numpy as np
import ast
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.utils.config_utils import load_config
from src.utils.path_utils import get_data_path

class PostRecommendationMLModel:
    def __init__(self):
        config = load_config()
        self.posts_df = pd.read_csv(get_data_path(config["data"]["post"]))
        self.user_df = pd.read_csv(get_data_path(config["data"]["user"]))
        self._preprocess()
        self._build_tfidf()

    def _preprocess(self):
        # tags, images 컬럼 파싱
        self.posts_df['tags'] = self.posts_df['tags'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
        self.posts_df['images'] = self.posts_df['images'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
        # 게시글별 통합 텍스트(태그 + 본문)
        self.posts_df['post_text'] = self.posts_df.apply(
            lambda row: " ".join(row['tags']) + " " + str(row['content']), axis=1
        )

    def _build_tfidf(self):
        # 전체 게시글 텍스트 임베딩
        self.tfidf = TfidfVectorizer()
        self.tfidf_matrix = self.tfidf.fit_transform(self.posts_df['post_text'])

    def get_user_tags(self, user_id: int) -> List[str]:
        user_row = self.user_df[self.user_df["user_id"] == user_id]
        if user_row.empty:
            return []
        tags = user_row.iloc[0]["tags"]
        if isinstance(tags, str):
            try:
                tags = ast.literal_eval(tags)
            except Exception:
                tags = tags.split(",")
        return [t.strip() for t in tags if t.strip()]

    def recommend_posts(self, user_id: int, page: int = 0, size: int = 6) -> list[int]:
        tags = self.get_user_tags(user_id)
        if not tags:
            return []

        # 1. 50자 이상 본문 필터
        mask = self.posts_df['content'].apply(lambda x: isinstance(x, str) and len(x) >= 50).to_numpy()
        filtered_indices = np.where(mask)[0]
        if len(filtered_indices) == 0:
            return []

        filtered_tags = self.posts_df['tags'].iloc[filtered_indices]
        filtered_board_ids = self.posts_df['board_id'].iloc[filtered_indices]

        # 2. 태그 유사도(자카드)만 계산
        def jaccard_similarity(tags1, tags2):
            set1, set2 = set(tags1), set(tags2)
            if not set1 or not set2:
                return 0.0
            return len(set1 & set2) / len(set1 | set2)

        sims = filtered_tags.apply(lambda review_tags: jaccard_similarity(review_tags, tags)).to_numpy()

        # 3. 정렬 및 페이지네이션
        start = page * size
        end = start + size
        top_indices = sims.argsort()[::-1][start:end]
        board_ids = [int(filtered_board_ids.iloc[idx]) for idx in top_indices]
        return board_ids

