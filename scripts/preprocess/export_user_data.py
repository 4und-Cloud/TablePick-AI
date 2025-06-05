import pandas as pd
from sqlalchemy import create_engine
from src.utils.path_utils import get_data_path

save_path = get_data_path('external', 'user_data.csv', mkdir=True)

engine = create_engine('mysql+pymysql://tablepick:tablepick@localhost/tablepickdb?charset=utf8')

query = """
SELECT
  m.id AS user_id,
  m.nickname,
  m.gender,
  m.birthdate,
  GROUP_CONCAT(t.name) AS tags
FROM
  member m
LEFT JOIN member_tag mt ON m.id = mt.member_id
LEFT JOIN tag t ON mt.tag_id = t.id
GROUP BY m.id;
"""

df = pd.read_sql(query, engine)
df['tags'] = df['tags'].apply(lambda x: x.split(',') if pd.notna(x) else [])
df.to_csv(save_path, index=False, encoding='utf-8')
