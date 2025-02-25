# ─────────────────────────────────────────────
# data_fetcher.py
# ─────────────────────────────────────────────

import os
import json
import datetime
import pandas as pd

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build  # for GSC / GA / GA4 など

# 例：サービスアカウントJSONのパスを指定(GitHub Actionsの場合、Secretsに格納して環境変数で渡す)
SERVICE_ACCOUNT_JSON = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "service_account.json")

def get_credentials():
    """
    Service Accountキー(JSON文字列)を環境変数で受け取る想定。
    JSONファイルを渡すなら open() で読み込みも可。
    """
    if not SERVICE_ACCOUNT_JSON:
        raise ValueError("サービスアカウントのJSONが環境変数にありません。設定してください。")

    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/webmasters",
            "https://www.googleapis.com/auth/bigquery",
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
    )
    return creds


def fetch_gsc_data(site_url: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Search Console APIを叩いて、クエリ/URL単位のクリックやインプレなどを取得し、Pandas DataFrameで返す例。
    """
    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)  # 本当は webmasters() 等

    request_body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query","page"],
        "rowLimit": 1000,
    }

    # 実際には:
    # response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
    # などの呼び出しが必要

    # ここではダミー返却
    data = {
        "query": ["keyword1", "keyword2"],
        "page": ["https://good-apps.jp/xxx", "https://good-apps.jp/yyy"],
        "clicks": [10, 5],
        "impressions": [100, 80],
        "ctr": [0.1, 0.0625],
        "position": [3.5, 7.2],
    }
    df = pd.DataFrame(data)
    return df


def fetch_bigquery_data(sql: str, project_id: str) -> pd.DataFrame:
    """
    BigQueryからSQLを実行し、DataFrameで返す。
    """
    creds = get_credentials()
    client = bigquery.Client(credentials=creds, project=project_id)

    query_job = client.query(sql)
    rows = list(query_job.result())
    if not rows:
        return pd.DataFrame()

    # スキーマから列名を取り出してDataFrame化
    columns = [field.name for field in rows[0].keys()]
    data = [list(row.values()) for row in rows]
    df = pd.DataFrame(data, columns=columns)
    return df


def fetch_ga4_data(property_id: str, start_date="7daysAgo", end_date="today") -> pd.DataFrame:
    """
    GA4 Data APIからメトリクスを取得してDataFrame化する例。
    """
    creds = get_credentials()
    analyticsdata = build("analyticsdata", "v1beta", credentials=creds)
    # v1 or v1beta で使い方が異なる場合あり

    body = {
        "property": f"properties/{property_id}",
        "metrics": [
            {"name": "screenPageViews"},
            {"name": "engagementRate"},
            {"name": "conversions"}
        ],
        "dimensions": [
            {"name": "pageLocation"}
        ],
        "dateRanges": [
            {"startDate": start_date, "endDate": end_date}
        ],
        "limit": 1000
    }
    response = analyticsdata.properties().runReport(
        property=f"properties/{property_id}",
        body=body
    ).execute()

    rows = response.get("rows", [])
    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        dimVals = r.get("dimensionValues", [])
        metVals = r.get("metricValues", [])
        records.append({
            "pageLocation": dimVals[0]["value"] if dimVals else None,
            "screenPageViews": metVals[0]["value"] if len(metVals)>0 else None,
            "engagementRate": metVals[1]["value"] if len(metVals)>1 else None,
            "conversions": metVals[2]["value"] if len(metVals)>2 else None,
        })
    df = pd.DataFrame(records)
    return df


def main_fetch_all():
    """
    まとめてデータを取得 → 必要に応じて結合 / 加工し、CSVなどに書き出す処理の例。
    """
    # 例1) GSCデータ
    site_url = "sc-domain:good-apps.jp"  # または "https://good-apps.jp/"
    gsc_df = fetch_gsc_data(site_url, "2025-01-01", "2025-01-31")

    # 例2) BigQueryデータ
    sql = "SELECT * FROM `your_project.your_dataset.your_table` LIMIT 100"
    project_id = "741349417998"  # 仮
    bq_df = fetch_bigquery_data(sql, project_id)

    # 例3) GA4データ
    ga4_property_id = "378700912"
    ga4_df = fetch_ga4_data(ga4_property_id)

    # 必要に応じて結合やconcatを行う
    # ここではサンプルとして gsc_df のみ CSV化
    merged_df = gsc_df
    merged_df.to_csv("merged_data.csv", index=False)

    print("Data fetch & merge completed.")


# ─────────────────────────────────────────────
# streamlit_app.py
# ─────────────────────────────────────────────

import streamlit as st
import pandas as pd
import numpy as np
from data_fetcher import main_fetch_all

def load_data():
    """
    data_fetcher.py の main_fetch_all() などを実行して
    出力された merged_data.csv を読み込む想定。
    """
    try:
        df = pd.read_csv("merged_data.csv")
    except:
        df = pd.DataFrame(columns=["query","page","clicks","impressions","ctr","position"])
    return df

def streamlit_main():
    st.title("G!A SEO指標：リライト優先管理ツール")

    # ---------------------------
    # サイドバーの「データ更新ボタン」
    # ---------------------------
    if st.sidebar.button("最新APIデータを取得/更新"):
        with st.spinner("データ取得中..."):
            main_fetch_all()  # BigQuery, GSC, GA4 などをまとめて取得
        st.sidebar.success("データを更新しました。")

    # ---------------------------
    # データをロード
    # ---------------------------
    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。左のボタンで取得してください。")
        return

    # カラム例: [query, page, clicks, impressions, ctr, position, ...]
    # デモ用にカラムが無い場合は追加
    if "rewrite_priority" not in df.columns:
        df["rewrite_priority"] = np.random.randint(1, 6, size=len(df))  # 1~5のダミー
    if "rewrite_done" not in df.columns:
        df["rewrite_done"] = False

    # ---------------------------
    # リライト優先度のソート
    # ---------------------------
    sort_order = st.selectbox("ソート順", ["優先度が高い順", "優先度が低い順"], index=0)
    ascending = (sort_order == "優先度が低い順")
    df_sorted = df.sort_values("rewrite_priority", ascending=ascending)

    st.subheader("KW一覧 (リライト優先度ソート済)")
    st.dataframe(df_sorted.reset_index(drop=True))

    # ---------------------------
    # リライト状況の更新
    # ---------------------------
    st.markdown("---")
    st.subheader("リライト状況の更新")

    # 対象キーワードを選択
    # 万が一、query が無い or 重複時の扱いなどは運用次第
    if df_sorted["query"].isnull().all():
        st.warning("query列に値がありません。")
        return

    # selectbox の要素が空にならないようユニーク化 & 欠損除外
    unique_queries = df_sorted["query"].dropna().unique()
    if len(unique_queries) == 0:
        st.warning("KWが存在しないため、更新できません。")
        return

    selected_row = st.selectbox(
        "リライト状況を更新するKWを選択",
        unique_queries
    )

    # フィルタして該当行を得る
    filtered_df = df_sorted[df_sorted["query"] == selected_row]
    if len(filtered_df) == 0:
        st.warning("選択されたKWのデータが見つかりません。")
        return

    # 最初の1行を抜き出す
    row_data = filtered_df.iloc[0]

    st.write(f"キーワード: {row_data.get('query','')}")
    st.write(f"URL: {row_data.get('page','')}")
    st.write(f"現在のリライト優先度: {row_data.get('rewrite_priority','')}")
    st.write(f"現在のリライト状況: {'済' if row_data.get('rewrite_done', False) else '未'}")

    # リライト済みに更新ボタン
    if st.button("リライト済みにする"):
        # df_sortedのインデックスを逆引きして、df自体を更新
        idx = filtered_df.index
        df.loc[idx, "rewrite_done"] = True

        # TODO: GoogleSpreadsheetやBigQueryに書き戻しするならここで実装
        st.success(f"『{selected_row}』をリライト済みに更新しました。")

    st.markdown("---")
    st.write("© 2025 Good-Apps.jp など")

if __name__ == "__main__":
    streamlit_main()
