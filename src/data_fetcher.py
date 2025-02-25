# data_fetcher.py

import os
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ▼ ここをあなたのスプレッドシートIDに置き換えてください
SPREADSHEET_ID = "1X6beVQYQsCKl2EV7yHg4y182EI0RJdJBaNGtcuX2bwo"

# ▼ サービスアカウントのJSONキーを環境変数から読み取る
SERVICE_ACCOUNT_JSON = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "")

def get_gspread_client():
    """
    gspread で Sheets にアクセスするための認証クライアントを返す。
    SERVICE_ACCOUNT_JSON が JSON文字列で環境変数に設定されている想定。
    """
    if not SERVICE_ACCOUNT_JSON:
        raise ValueError("サービスアカウントJSONが見つかりません。環境変数 GCP_SERVICE_ACCOUNT_JSON を設定してください。")
    
    info = json.loads(SERVICE_ACCOUNT_JSON)
    
    # gspread + oauth2client を使う場合のスコープ
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly", 
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

def fetch_data_from_query_sheet() -> pd.DataFrame:
    """
    Googleスプレッドシートの「query_貼付」シートの値を読み込み、DataFrameに変換する。
    シートの1行目にヘッダーが含まれる想定。
    """
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    wks = sh.worksheet("query_貼付")  # シート名
    
    # シート全体を取得 (1行目がカラム名という想定)
    all_values = wks.get_all_values()
    if len(all_values) < 2:
        # ヘッダーしか無い or 空
        return pd.DataFrame()
    
    # 1行目をカラム名、2行目以降をデータとしてDataFrame化
    header = all_values[0]
    data_rows = all_values[1:]
    df = pd.DataFrame(data_rows, columns=header)
    return df

def main_fetch_all():
    """
    「query_貼付」シートのデータを CSV に保存。
    """
    df = fetch_data_from_query_sheet()
    df.to_csv("sheet_query_data.csv", index=False, encoding="utf-8-sig")
    print("シート 'query_貼付' のデータを 'sheet_query_data.csv' に出力しました。")
