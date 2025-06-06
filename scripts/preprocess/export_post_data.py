import pandas as pd
from sqlalchemy import create_engine
from src.utils.path_utils import get_data_path

# 저장 경로 지정
save_path = get_data_path('external', 'post_data.csv', mkdir=True)

# SQLAlchemy 엔진 생성
engine = create_engine('mysql+pymysql://tablepick:tablepick@localhost/tablepickdb?charset=utf8')

query = """
SELECT
  b.id AS board_id,
  b.member_id,
  m.nickname,
  b.content,
  b.created_at,
  GROUP_CONCAT(DISTINCT t.name) AS tags,
  GROUP_CONCAT(DISTINCT bi.image_url) AS images
FROM
  board b
LEFT JOIN member m ON b.member_id = m.id
LEFT JOIN board_tag bt ON b.id = bt.board_id
LEFT JOIN tag t ON bt.tag_id = t.id
LEFT JOIN board_image bi ON b.id = bi.board_id
GROUP BY b.id
HAVING images IS NOT NULL;
"""

# pandas에서 SQLAlchemy 엔진으로 바로 읽기
df = pd.read_sql(query, engine)

# 태그와 이미지 컬럼을 리스트로 변환
df['content'] = df['content'].str.replace('\n', ' ').str.replace('\r', ' ')
df['tags'] = df['tags'].apply(lambda x: x.split(',') if pd.notna(x) else [])
df['images'] = df['images'].apply(lambda x: x.split(',') if pd.notna(x) else [])

df.to_csv(save_path, index=False, encoding='utf-8')
