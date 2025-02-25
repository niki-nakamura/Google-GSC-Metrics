# data_fetcher.py

import os
import json
import datetime
import pandas as pd

from google.oauth2 import service_account
from google.cloud import bigquery

SERVICE_ACCOUNT_JSON = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "service_account.json")

def get_credentials():
    """
    Service Accountキー(JSON文字列)を環境変数で受け取る想定。
    """
    if not SERVICE_ACCOUNT_JSON:
        raise ValueError("サービスアカウントのJSONが環境変数にありません。")

    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/bigquery",
        ],
    )
    return creds

def fetch_bigquery_data(sql: str, project_id: str) -> pd.DataFrame:
    """
    共通のBigQuery実行関数
    """
    creds = get_credentials()
    client = bigquery.Client(credentials=creds, project=project_id)

    query_job = client.query(sql)
    rows = list(query_job.result())
    if not rows:
        return pd.DataFrame()

    # スキーマから列名を取得
    columns = [field.name for field in rows[0].keys()]
    data = [list(row.values()) for row in rows]
    df = pd.DataFrame(data, columns=columns)
    return df

def fetch_wp_content_7days() -> pd.DataFrame:
    """
    指定のクエリを実行し、直近7日間の wp_content_by_result_* テーブルデータを取得
    """
    sql = """
SELECT
  event_date,
  CONTENT_TYPE,
  POST_ID,
  post_title,
  session,
  page_view,
  click_app_store,
  imp,
  click,
  sum_position,
  avg_position,
  sales,
  app_link_click,
  cv
FROM `afmedia.seo_bizdev.wp_content_by_result_*`
WHERE 
  _TABLE_SUFFIX BETWEEN
    FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
;
"""
    project_id = "afmedia"  # 適切なProject IDに置き換えてください
    df = fetch_bigquery_data(sql, project_id)
    return df

def main_fetch_all():
    """
    必要に応じてまとめて色々Fetchしたい場合はここで実装。
    今回は wp_content_7days() の結果だけをCSV化して終わりにする例。
    """
    df_wp = fetch_wp_content_7days()
    df_wp.to_csv("wp_content_latest.csv", index=False)
    print("Data fetch & CSV保存完了")
