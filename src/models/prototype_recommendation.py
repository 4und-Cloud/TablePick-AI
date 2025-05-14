import pandas as pd
import json
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from math import radians, sin, cos, sqrt, atan2
import os
from collections import Counter

class RecommendationModel:
    def __init__(self):
        self.df = None
        self.tfidf_matrix = None
        self.cosine_sim = None
        self.tfidf = None
        self.initialize_model()
    
    def initialize_model(self):
        # 프로젝트 루트 경로 찾기
        script_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
        project_root = os.path.abspath(os.path.join(script_dir, '../..'))  # 프로젝트 루트
        file_path = os.path.join(project_root, 'data/external/google_gangnam_crawling_data.csv')
        
        # 데이터 로드
        self.df = pd.read_csv(file_path)
        
        # 데이터 전처리
        self.preprocess_data()
        
        # TF-IDF 행렬 생성
        self.create_tfidf_matrix()
        
        print(f"모델 초기화 완료: {len(self.df)} 개의 음식점 데이터 로드됨")
    
    def preprocess_data(self):
        # 결측치 처리
        self.df = self.df.fillna("")
        
        # 태그 정보 처리
        self.df['음식점_태그'] = self.df['음식점_태그'].apply(self.parse_json_field)
        
        # 특징 추출
        self.df["combined_features"] = self.df.apply(self.combine_features, axis=1)
    
    @staticmethod
    def parse_json_field(json_str):
        if isinstance(json_str, str):
            try:
                return ast.literal_eval(json_str)
            except:
                try:
                    return json.loads(json_str)
                except:
                    return json_str
        return json_str
    
    @staticmethod
    def combine_features(row):
        # 태그 추출
        tags = ""
        if isinstance(row["음식점_태그"], list):
            tags = " ".join([tag["tags"] for tag in row["음식점_태그"] if "tags" in tag])

        return f"{tags}".strip()
    
    def create_tfidf_matrix(self):
        # TF-IDF 벡터화
        self.tfidf = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.tfidf.fit_transform(self.df["combined_features"])
        
        # 코사인 유사도 계산
        self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
    
    def recommend_by_tags(self, tags, top_n=10):
        # 태그가 비어있는 경우 처리
        if not tags:
            return pd.DataFrame()
        
        # 사용자 입력 태그를 텍스트로 변환
        user_input = " ".join(tags)
        
        # 사용자 입력을 벡터화
        user_tfidf = self.tfidf.transform([user_input])
        
        # 유사도 계산
        sim_scores = list(enumerate(cosine_similarity(user_tfidf, self.tfidf_matrix)[0]))
        
        # 유사도 기준 정렬
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # 상위 N개 음식점 인덱스
        top_indices = [i[0] for i in sim_scores[:top_n]]
        
        # 추천 음식점 반환
        recommendations = self.df.iloc[top_indices][["음식점_이름", "주소", "카테고리"]]
        return recommendations


    def recommend_by_restaurant(self, restaurant_idx, top_n=10):
        # 인덱스 범위 확인
        if restaurant_idx < 0 or restaurant_idx >= len(self.df):
            return pd.DataFrame()
        
        # 유사도 점수 가져오기
        sim_scores = list(enumerate(self.cosine_sim[restaurant_idx]))
        
        # 자기 자신 제외 및 유사도 기준 정렬
        sim_scores = sorted([(i, score) for i, score in sim_scores if i != restaurant_idx], 
                           key=lambda x: x[1], reverse=True)
        
        # 상위 N개 음식점 인덱스
        top_indices = [i[0] for i in sim_scores[:top_n]]
        
        # 추천 음식점 반환
        return self.df.iloc[top_indices][["음식점_이름", "주소", "메뉴_정보", "카테고리", "위도", "경도", "전화번호"]]
    
    def recommend_by_preferences(self, preferences, user_lat=None, user_lon=None, top_n=10, max_distance_km=5):
        # 사용자 선호도를 텍스트로 변환
        user_input = " ".join(preferences)
        
        # 사용자 입력을 벡터화
        user_tfidf = self.tfidf.transform([user_input])
        
        # 유사도 계산
        sim_scores = list(enumerate(cosine_similarity(user_tfidf, self.tfidf_matrix)[0]))
        
        # 유사도 기준 정렬
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # 상위 N*2개 음식점 인덱스 (위치 필터링을 고려해 더 많이 가져옴)
        top_indices = [i[0] for i in sim_scores[:top_n*2]]
        recommendations = self.df.iloc[top_indices][["음식점_이름", "주소", "메뉴_정보", "카테고리", "위도", "경도", "전화번호"]]
        
        # 위치 기반 필터링 (선택적)
        if user_lat is not None and user_lon is not None:
            recommendations = self.filter_by_location(recommendations, user_lat, user_lon, max_distance_km)
        
        return recommendations.head(top_n)
    
    @staticmethod
    def filter_by_location(recommendations, user_lat, user_lon, max_distance_km=5):
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # 지구 반지름 (km)
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        
        # 사용자 위치와 음식점 거리 계산
        recommendations["distance"] = recommendations.apply(
            lambda row: haversine(user_lat, user_lon, row["위도"], row["경도"]) 
                       if pd.notna(row["위도"]) and pd.notna(row["경도"]) else float('inf'), 
            axis=1
        )
        
        # 최대 거리 이내 음식점만 반환
        return recommendations[recommendations["distance"] <= max_distance_km].sort_values("distance")
    
    def load_user_data(self, user_id):
        """
        사용자 ID를 기반으로 사용자 태그 데이터를 불러옵니다.
        """
        # 실제 구현에서는 데이터베이스에서 사용자 데이터를 조회합니다
        # 예시 코드:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        user_data_path = os.path.join(project_root, 'data/external/user_data.csv')
        
        # 파일이 존재하는지 확인
        if not os.path.exists(user_data_path):
            print(f"사용자 데이터 파일이 존재하지 않습니다: {user_data_path}")
            # 예시 태그 반환 (실제 구현에서는 적절히 수정)
            return ["한식", "분위기좋은", "가성비"]
        
        # 사용자 데이터 로드
        user_df = pd.read_csv(user_data_path)
        
        # 특정 사용자 ID의 데이터 필터링
        user_data = user_df[user_df['user_id'] == user_id]
        
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
        # 실제 구현에서는 데이터베이스에서 사용자 방문 기록을 조회합니다
        # 예시 코드:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        visit_data_path = os.path.join(project_root, 'data/external/user_visits.csv')
        
        # 파일이 존재하는지 확인
        if not os.path.exists(visit_data_path):
            print(f"방문 기록 파일이 존재하지 않습니다: {visit_data_path}")
            return []
        
        # 방문 기록 데이터 로드
        visit_df = pd.read_csv(visit_data_path)
        
        # 특정 사용자 ID의 방문 기록 필터링
        user_visits = visit_df[visit_df['user_id'] == user_id]
        
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
        # 실제 구현에서는 데이터베이스에서 모든 사용자 데이터를 조회합니다
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        user_data_path = os.path.join(project_root, 'data/external/user_data.csv')
        
        # 파일이 존재하는지 확인
        if not os.path.exists(user_data_path):
            print(f"사용자 데이터 파일이 존재하지 않습니다: {user_data_path}")
            return []
        
        # 사용자 데이터 로드
        user_df = pd.read_csv(user_data_path)
        
        # 현재 사용자의 태그
        current_user = user_df[user_df['user_id'] == user_id]
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
        for idx, row in user_df.iterrows():
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
