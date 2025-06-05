import pandas as pd
import ast
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.utils.config_utils import load_config
from src.utils.path_utils import get_data_path

class PostRecommendationMLModel:
    def __init__(self):
        config = load_config()
        self.posts_df = pd.read_csv(get_data_path(config["data"]["restaurant"]))
        self.user_df = pd.read_csv(get_data_path(config["data"]["user"]))
        self._preprocess()
        self._build_tfidf()

    def _preprocess(self):
        # 리뷰 파싱
        self.posts_df['리뷰'] = self.posts_df['리뷰'].apply(self._safe_parse_json)
        # 게시글별 통합 텍스트(태그 + 본문)
        self.posts_df['post_text'] = self.posts_df['리뷰'].apply(self._combine_review_text)

    @staticmethod
    def _safe_parse_json(x):
        if isinstance(x, str) and x and x != "nan":
            try:
                return ast.literal_eval(x)
            except Exception:
                return []
        return [] if pd.isna(x) else x

    @staticmethod
    def _combine_review_text(reviews):
        # 리뷰 리스트에서 태그와 게시글 본문 합침
        texts = []
        if isinstance(reviews, list):
            for r in reviews:
                tags = " ".join(r.get("태그", []))
                text = r.get("게시글", "")
                texts.append(f"{tags} {text}")
        return " ".join(texts)

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

    def recommend_posts(self, user_id: int, top_n: int = 10) -> List[Dict[str, Any]]:
        tags = self.get_user_tags(user_id)
        if not tags:
            return []

        # 사용자 태그를 하나의 쿼리 텍스트로 만듦
        user_query = " ".join(tags)
        user_vec = self.tfidf.transform([user_query])
        sims = cosine_similarity(user_vec, self.tfidf_matrix)[0]
        top_indices = sims.argsort()[::-1][:top_n]

        results = []
        for idx in top_indices:
            row = self.posts_df.iloc[idx]
            # 원본 리뷰 중 사용자 태그와 가장 유사한 리뷰 1~3개 추출(자카드 유사도 기준)
            reviews = row["리뷰"]
            best_reviews = self.select_recommended_reviews(reviews, tags, top_n=3)
            for review in best_reviews:
                results.append({
                    "restaurant_name": row["음식점_이름"],
                    "address": row["주소"],
                    "review": review.get("게시글", ""),
                    "tags": review.get("태그", []),
                    "images": review.get("이미지", []),
                    "review_time": review.get("작성시간", "")
                })
        return results[:top_n]

    @staticmethod
    def select_recommended_reviews(reviews, preferred_tags, top_n=3):
        def jaccard(tags1, tags2):
            set1, set2 = set(tags1), set(preferred_tags)
            if not set1 or not set2:
                return 0.0
            return len(set1 & set2) / len(set1 | set2)
        filtered = [r for r in reviews if r.get("이미지") and len(r["이미지"]) > 0]
        filtered = [r for r in filtered if len(r.get("게시글", "")) >= 30]
        for r in filtered:
            r["tag_similarity"] = jaccard(r.get("태그", []), preferred_tags)
        filtered = sorted(filtered, key=lambda r: r["tag_similarity"], reverse=True)
        return filtered[:top_n]
