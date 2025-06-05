import pandas as pd
import ast
import os
import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from math import radians, sin, cos, sqrt, atan2
from collections import Counter
from src.utils.path_utils import get_data_path
from src.utils.config_utils import load_config

class RecommendationModel:
    def __init__(self):
        # 1. config, 경로, 데이터프레임 로딩
        config = load_config()
        self.user_data_path = get_data_path(config["data"]["user"])
        self.restaurant_data_path = get_data_path(config["data"]["restaurant"])
        self.visit_data_path = get_data_path(config["data"]["visit"])

        self.user_df = pd.read_csv(self.user_data_path)
        self.restaurant_df = pd.read_csv(self.restaurant_data_path)
        # self.visit_df = pd.read_csv(self.visit_data_path)

        # 2. 전처리 및 모델 구축
        self.df = self.restaurant_df  # 또는 별도 전처리 결과
        self.tfidf_matrix = None
        self.tfidf = None
        self.cosine_sim = None
        self._load_and_preprocess()
        self._build_tfidf_matrix()

        print(f"모델 초기화 완료: {len(self.df)} 개의 음식점 데이터 로드됨")

    def _load_and_preprocess(self):
        self.df = self.df.fillna("")

        # JSON 컬럼 파싱
        self.df['리뷰'] = self.df['리뷰'].apply(self._safe_parse_json)
        self.df['메뉴_정보'] = self.df['메뉴_정보'].apply(self._safe_parse_json)
        self.df['영업시간'] = self.df['영업시간'].apply(self._safe_parse_json)
        # 필요시 음식점_사진 등도 파싱

        # 음식점 태그: 모든 리뷰의 태그를 합침(flatten)
        self.df['음식점_태그'] = self.df['리뷰'].apply(self._extract_tags_from_reviews)

        # TF-IDF 피처 생성용 텍스트
        self.df['combined_features'] = self.df.apply(self._combine_features, axis=1)

    @staticmethod
    def _safe_parse_json(x):
        if isinstance(x, str) and x and x != "nan":
            try:
                return ast.literal_eval(x)
            except Exception:
                return []
        return [] if pd.isna(x) else x

    @staticmethod
    def _extract_tags_from_reviews(reviews):
        tags = []
        if isinstance(reviews, list):
            for review in reviews:
                tags.extend(review.get("태그", []))
        return tags

    @staticmethod
    def _extract_review_texts(reviews):
        texts = []
        if isinstance(reviews, list):
            for review in reviews:
                text = review.get("게시글", "")
                if text:
                    texts.append(text)
        return " ".join(texts)

    @staticmethod
    def _extract_menu_names(menu_info):
        names = []
        if isinstance(menu_info, list):
            for menu in menu_info:
                name = menu.get("메뉴명", "")
                if name:
                    names.append(name)
        return " ".join(names)

    def _combine_features(self, row):
        tags = " ".join(row['음식점_태그'])
        category = row.get("카테고리", "")
        menu_names = self._extract_menu_names(row.get("메뉴_정보", []))
        review_texts = self._extract_review_texts(row.get("리뷰", []))
        return f"{tags} {category} {menu_names} {review_texts}".strip()

    def _build_tfidf_matrix(self):
        self.tfidf = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.tfidf.fit_transform(self.df["combined_features"])
        self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)

    def recommend_by_tags(self, tags, top_n=10):
        if not tags:
            return pd.DataFrame()
        user_input = " ".join(tags)
        user_tfidf = self.tfidf.transform([user_input])
        sim_scores = list(enumerate(cosine_similarity(user_tfidf, self.tfidf_matrix)[0]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        top_indices = [i[0] for i in sim_scores[:top_n]]
        recommendations = self.df.iloc[top_indices][["음식점_이름", "주소", "카테고리", "음식점_사진"]]
        recommendations.index = top_indices
        return recommendations

    def recommend_by_restaurant(self, restaurant_idx, top_n=10):
        if restaurant_idx < 0 or restaurant_idx >= len(self.df):
            return pd.DataFrame()
        sim_scores = list(enumerate(self.cosine_sim[restaurant_idx]))
        sim_scores = sorted([(i, score) for i, score in sim_scores if i != restaurant_idx], key=lambda x: x[1], reverse=True)
        top_indices = [i[0] for i in sim_scores[:top_n]]
        recommendations = self.df.iloc[top_indices][["음식점_이름", "주소", "카테고리", "음식점_사진"]]
        recommendations.index = top_indices
        return recommendations

    def recommend_by_preferences(self, preferences, user_lat=None, user_lon=None, top_n=10, max_distance_km=5):
        user_input = " ".join(preferences)
        user_tfidf = self.tfidf.transform([user_input])
        sim_scores = list(enumerate(cosine_similarity(user_tfidf, self.tfidf_matrix)[0]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        top_indices = [i[0] for i in sim_scores[:top_n*2]]
        recommendations = self.df.iloc[top_indices][["음식점_이름", "주소", "카테고리", "음식점_사진", "위도", "경도"]]
        recommendations.index = top_indices
        # 위치 필터링
        if user_lat is not None and user_lon is not None:
            recommendations = self._filter_by_location(recommendations, user_lat, user_lon, max_distance_km)
        return recommendations.head(top_n)

    @staticmethod
    def _filter_by_location(recommendations, user_lat, user_lon, max_distance_km=5):
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        recommendations = recommendations.copy()
        recommendations["distance"] = recommendations.apply(
            lambda row: haversine(user_lat, user_lon, float(row["위도"]), float(row["경도"]))
            if pd.notna(row["위도"]) and pd.notna(row["경도"]) else float('inf'),
            axis=1
        )
        return recommendations[recommendations["distance"] <= max_distance_km].sort_values("distance")

    
    def load_user_data(self, user_id):
        """
        사용자 ID를 기반으로 사용자 태그 데이터를 불러옵니다.
        """
        # 파일이 존재하는지 확인
        if not os.path.exists(self.user_data_path):
            print(f"사용자 데이터 파일이 존재하지 않습니다: {self.user_data_path}")
            # 예시 태그 반환 (실제 구현에서는 적절히 수정)
            return ["한식", "분위기좋은", "가성비"]
        
        # 특정 사용자 ID의 데이터 필터링
        user_data = self.user_df[self.user_df['user_id'] == user_id]
        
        if user_data.empty:
            print(f"사용자 ID {user_id}에 대한 데이터를 찾을 수 없습니다.")
            # 예시 태그 반환 (실제 구현에서는 적절히 수정)
            return ["한식", "분위기좋은", "가성비"]
        
        # 사용자 태그 추출
        user_tags = user_data['tags'].values[0]
        if isinstance(user_tags, str):
            # 문자열 형태의 태그를 리스트로 변환
            try:
                user_tags = ast.literal_eval(user_tags)
            except:
                user_tags = user_tags.split(',')
        
        return user_tags
    
    def recommend_by_user_id(self, user_id, top_n=5):
        """
        사용자 ID를 기반으로 음식점을 추천합니다.
        """
        # 사용자 태그 데이터 로드
        user_tags = self.load_user_data(user_id)
        
        if not user_tags:
            print(f"사용자 ID {user_id}에 대한 추천을 생성할 수 없습니다.")
            return pd.DataFrame()
        
        # 사용자 태그 기반 추천
        recommendations = self.recommend_by_preferences(user_tags, top_n=top_n)
        
        # 결과에 식당 ID 추가
        recommendations['restaurant_id'] = recommendations.index
        
        return recommendations[["restaurant_id", "음식점_이름", "주소", "카테고리"]]
    
    def load_user_visit_history(self, user_id):
        """
        사용자의 방문 기록을 불러옵니다.
        """
        
        # 파일이 존재하는지 확인
        if not os.path.exists(self.visit_data_path):
            print(f"방문 기록 파일이 존재하지 않습니다: {self.visit_data_path}")
            return []
        
        # 특정 사용자 ID의 방문 기록 필터링
        user_visits = self.visit_df[self.visit_df['user_id'] == user_id]
        
        if user_visits.empty:
            print(f"사용자 ID {user_id}의 방문 기록이 없습니다.")
            return []
        
        # 방문한 식당 ID 목록 반환
        return user_visits['restaurant_id'].tolist()
    
    def recommend_by_user_id_advanced(self, user_id, top_n=5):
        """
        사용자 태그와 방문 기록을 모두 고려한 고급 추천 시스템
        """
        # 사용자 태그 데이터 로드
        user_tags = self.load_user_data(user_id)
        
        if not user_tags:
            print(f"사용자 ID {user_id}에 대한 태그 데이터가 없습니다.")
            return pd.DataFrame()
        
        # 사용자 방문 기록 로드
        visited_restaurants = self.load_user_visit_history(user_id)
        
        # 태그 기반 추천 (방문 기록 제외)
        recommendations = self.recommend_by_preferences(user_tags, top_n=top_n*2)
        
        # 이미 방문한 식당 제외
        if visited_restaurants:
            recommendations = recommendations[~recommendations.index.isin(visited_restaurants)]
        
        # 상위 N개 결과 반환
        recommendations = recommendations.head(top_n)
        recommendations['restaurant_id'] = recommendations.index
        
        return recommendations[["restaurant_id", "음식점_이름", "주소", "카테고리"]]
    
    def find_similar_users(self, user_id, top_n=10):
        """
        유사한 태그를 가진 사용자를 찾습니다.
        """
        
        # 파일이 존재하는지 확인
        if not os.path.exists(self.user_data_path):
            print(f"사용자 데이터 파일이 존재하지 않습니다: {self.user_data_path}")
            return []
        
        # 현재 사용자의 태그
        current_user = self.user_df[self.user_df['user_id'] == user_id]
        if current_user.empty:
            return []
        
        current_tags = current_user['tags'].values[0]
        if isinstance(current_tags, str):
            try:
                current_tags = ast.literal_eval(current_tags)
            except:
                current_tags = current_tags.split(',')
        
        # 다른 사용자와의 유사도 계산
        similarities = []
        for idx, row in self.user_df.iterrows():
            if row['user_id'] == user_id:
                continue
                
            other_tags = row['tags']
            if isinstance(other_tags, str):
                try:
                    other_tags = ast.literal_eval(other_tags)
                except:
                    other_tags = other_tags.split(',')
            
            # 자카드 유사도 계산
            intersection = len(set(current_tags) & set(other_tags))
            union = len(set(current_tags) | set(other_tags))
            similarity = intersection / union if union > 0 else 0
            
            similarities.append((row['user_id'], similarity))
        
        # 유사도 기준 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 N명의 유사 사용자 반환
        return [user_id for user_id, _ in similarities[:top_n]]
    
    def recommend_collaborative(self, user_id, top_n=10):
        """
        협업 필터링 기반 추천
        """
        # 유사한 사용자 찾기
        similar_users = self.find_similar_users(user_id)
        
        if not similar_users:
            print(f"사용자 ID {user_id}와 유사한 사용자를 찾을 수 없습니다.")
            return pd.DataFrame()
        
        # 유사 사용자들의 방문 기록 수집
        all_visited = []
        for similar_user in similar_users:
            visited = self.load_user_visit_history(similar_user)
            all_visited.extend(visited)
        
        # 방문 빈도 계산
        visit_counts = Counter(all_visited)
        
        # 현재 사용자가 방문한 식당 제외
        user_visited = set(self.load_user_visit_history(user_id))
        for restaurant in user_visited:
            if restaurant in visit_counts:
                del visit_counts[restaurant]
        
        # 가장 많이 방문한 식당 추출
        top_restaurants = [restaurant for restaurant, _ in visit_counts.most_common(top_n)]
        
        # 추천 식당 정보 반환
        if top_restaurants:
            recommendations = self.df.loc[top_restaurants]
            recommendations['restaurant_id'] = recommendations.index
            return recommendations[["restaurant_id", "음식점_이름", "주소", "카테고리"]]
        else:
            return pd.DataFrame()
    
    def recommend_hybrid(self, user_id, top_n=5):
        """
        콘텐츠 기반 필터링과 협업 필터링을 결합한 하이브리드 추천
        """
        # 콘텐츠 기반 추천
        content_recommendations = self.recommend_by_user_id_advanced(user_id, top_n=top_n)
        
        # 협업 필터링 기반 추천
        collaborative_recommendations = self.recommend_collaborative(user_id, top_n=top_n)
        
        # 두 결과 병합
        if not content_recommendations.empty and not collaborative_recommendations.empty:
            # 콘텐츠 기반 추천에 가중치 0.7, 협업 필터링 추천에 가중치 0.3 부여
            content_ids = set(content_recommendations['restaurant_id'])
            collab_ids = set(collaborative_recommendations['restaurant_id'])
            
            # 양쪽 모두에 있는 식당 (가중치 합산)
            common_ids = content_ids.intersection(collab_ids)
            
            # 콘텐츠 기반에만 있는 식당
            content_only = content_ids - common_ids
            
            # 협업 필터링에만 있는 식당
            collab_only = collab_ids - common_ids
            
            # 결과 병합 및 정렬
            final_ids = list(common_ids) + list(content_only) + list(collab_only)
            final_ids = final_ids[:top_n]
            
            # 최종 추천 결과 반환
            recommendations = self.df.loc[final_ids]
            recommendations['restaurant_id'] = recommendations.index
            return recommendations[["restaurant_id", "음식점_이름", "주소", "카테고리"]]
        elif not content_recommendations.empty:
            return content_recommendations.head(top_n)
        elif not collaborative_recommendations.empty:
            return collaborative_recommendations.head(top_n)
        else:
            return pd.DataFrame()


    def select_recommended_reviews(reviews, preferred_tags, top_n=3):
        """
        reviews: 리뷰 리스트 (각 리뷰는 dict, '태그' 키에 태그 리스트 포함)
        preferred_tags: 사용자의 선호 태그 리스트
        top_n: 반환할 추천 리뷰 개수
        """
        # 1. 사진 포함 여부
        filtered = [r for r in reviews if r.get("이미지") and len(r["이미지"]) > 0]
        # 2. 본문 길이 기준
        filtered = [r for r in filtered if len(r.get("게시글", "")) >= 50]
        if not filtered:
            return []

        # 3. 태그 유사도(자카드 유사도) 계산
        def jaccard_similarity(tags1, tags2):
            set1, set2 = set(tags1), set(tags2)
            if not set1 or not set2:
                return 0.0
            return len(set1 & set2) / len(set1 | set2)

        for r in filtered:
            review_tags = r.get("태그", [])
            r["tag_similarity"] = jaccard_similarity(review_tags, preferred_tags)
            # 최신순 정렬을 위해 datetime 파싱
            try:
                r["작성시간_dt"] = datetime.datetime.fromisoformat(r.get("작성시간", ""))
            except Exception:
                r["작성시간_dt"] = datetime.datetime.min

        # 4. 태그 유사도(우선), 최신순(보조)로 정렬
        filtered = sorted(
            filtered,
            key=lambda r: (r["tag_similarity"], r["작성시간_dt"]),
            reverse=True
        )

        # 5. 상위 N개 반환
        return filtered[:top_n]