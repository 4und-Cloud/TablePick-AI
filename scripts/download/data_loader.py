import os
from sqlalchemy import create_engine
import pandas as pd
from elasticsearch import Elasticsearch

class DataLoader:
    def __init__(self):
        # MySQL 환경 설정
        self.MYSQL_HOST = os.getenv("MYSQL_HOST")
        self.MYSQL_PORT = int(os.getenv("MYSQL_PORT"))
        self.MYSQL_USER = os.getenv("MYSQL_USER")
        self.MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        self.MYSQL_DB = os.getenv("MYSQL_DB")

        # SQLAlchemy 엔진 생성
        connection_string = f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        self.engine = create_engine(connection_string, echo=False)

        # Elasticsearch 설정
        self.ES_HOST = os.getenv("ES_HOST")
        self.es = Elasticsearch(self.ES_HOST)

    # 더 이상 pymysql 연결 객체 반환하지 않고, SQLAlchemy 엔진을 사용
    # 기존 fetch_xxx_df 함수에서 with 구문 제거, pd.read_sql(query, self.engine) 사용

    # 1️⃣ restaurant_df: 음식점 정보
    def fetch_restaurant_df(self):
        query = """
            WITH tag_counts AS (
            SELECT
                restaurant_id,
                tag_id,
                COUNT(*) AS tag_count
            FROM board_tag
            GROUP BY restaurant_id, tag_id
            ),
            ranked_tags AS (
            SELECT
                restaurant_id,
                tag_id,
                ROW_NUMBER() OVER (
                PARTITION BY restaurant_id
                ORDER BY tag_count DESC
                ) AS rnk
            FROM tag_counts
            )
            SELECT restaurant_id, tag_id
            FROM ranked_tags
            WHERE rnk <= 3;
        """
        df = pd.read_sql(query, self.engine)

        # tagId를 리스트로 집계
        grouped_df = df.groupby("restaurant_id")["tag_id"].apply(list).reset_index()
        return grouped_df

    # 2️⃣ review_df: 리뷰 정보
    def fetch_review_df(self):
        query = """
            WITH tag_counts AS (
                SELECT
                    board_id,
                    tag_id,
                    COUNT(*) AS tag_count
                FROM board_tag
                GROUP BY board_id, tag_id
            ),
            ranked_tags AS (
                SELECT
                    board_id,
                    tag_id,
                    ROW_NUMBER() OVER (PARTITION BY board_id ORDER BY tag_count DESC) AS rnk
                FROM tag_counts
            )
            SELECT board_id, tag_id
            FROM ranked_tags
            WHERE rnk <= 3;
        """
        df = pd.read_sql(query, self.engine)

        grouped_df = df.groupby("board_id")["tag_id"].apply(list).reset_index()
        return grouped_df

    # 3️⃣ user_data_df: 유저 선호 태그 등
    def fetch_user_data_df(self):
        query = """
            SELECT
                member_id,
                tag_id
            FROM member_tag
        """
        df = pd.read_sql(query, self.engine)

        grouped_df = df.groupby("member_id")["tag_id"].apply(list).reset_index()
        return grouped_df

    # 4️⃣ user_behavior_df: ES에서 과거 유저 행동 로그 (30일)
    def fetch_user_restaurant_df(self, days=30):
        query = {
            "size": 10000,
            "_source": ["userId", "targetId", "actionEventType", "timestamp"],
            "query": {
                "bool": {
                    "filter": [
                        {"terms": {"actionEventType": ["RESTAURANT_VIEW", "RESTAURANT_CLICK"]}},
                        {"range": {"@timestamp": {"gte": f"now-{days}d/d"}}}
                    ]
                }
            }
        }
        result = self.es.search(index="user-action-events", body=query)
        logs = [hit["_source"] for hit in result["hits"]["hits"]]
        df = pd.DataFrame(logs)
        if not df.empty:
            score_map = {"RESTAURANT_VIEW": 1.0, "RESTAURANT_CLICK": 2.0}
            df["score"] = df["actionEventType"].map(score_map)
            df = df.groupby(["userId", "targetId"]).agg({"score": "sum"}).reset_index()
            df.rename(columns={"userId": "member_id", "targetId": "restaurant_id"}, inplace=True)
        return df
    
    def fetch_user_board_df(self, days=30):
        query = {
            "size": 10000,
            "_source": ["userId", "targetId", "actionEventType", "timestamp"],
            "query": {
                "bool": {
                    "filter": [
                        {"terms": {"actionEventType": ["BOARD_VIEW", "BOARD_CLICK"]}},
                        {"range": {"@timestamp": {"gte": f"now-{days}d/d"}}}
                    ]
                }
            }
        }
        result = self.es.search(index="user-action-events", body=query)
        logs = [hit["_source"] for hit in result["hits"]["hits"]]
        df = pd.DataFrame(logs)
        if not df.empty:
            score_map = {"BOARD_VIEW": 1.0, "BOARD_CLICK": 2.0}
            df["score"] = df["actionEventType"].map(score_map)
            df = df.groupby(["userId", "targetId"]).agg({"score": "sum"}).reset_index()
            df.rename(columns={"userId": "member_id", "targetId": "board_id"}, inplace=True)
        return df


# ✅ 실행 예시
if __name__ == "__main__":
    loader = DataLoader()

    restaurant_df = loader.fetch_restaurant_df()
    print(f"[restaurant_df] {restaurant_df.shape}")

    review_df = loader.fetch_review_df()
    print(f"[review_df] {review_df.shape}")

    user_data_df = loader.fetch_user_data_df()
    print(f"[user_data_df] {user_data_df.shape}")

    user_restaurant_df = loader.fetch_user_restaurant_df()
    print(f"[user_restaurant_df] {user_restaurant_df.shape}")

    user_board_df = loader.fetch_user_board_df()
    print(f"[user_board_df] {user_board_df.shape}")
