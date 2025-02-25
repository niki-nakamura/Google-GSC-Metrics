# data_fetcher.py
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st  # ← Secretsを読むため

# ここは、該当スプレッドシートの ID を設定
SPREADSHEET_ID = "1X6beVQYQsCKl2EV7yHg4y182EI0RJdJBaNGtcuX2bwo"
SHEET_NAME = "query_貼付"

def get_gspread_client():
    """
    Streamlit の Secrets に格納した Service Account JSON を用いて認証し、
    gspread.Client を返す。
    """
    # secrets.toml で定義: [キー] GSPREAD_SERVICE_ACCOUNT_JSON = """{ ... }"""
    service_account_json_str = st.secrets["GSPREAD_SERVICE_ACCOUNT_JSON"]
    
    # JSON文字列をPythonのdictに変換
    info = json.loads(service_account_json_str)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(info, scopes)
    gc = gspread.authorize(credentials)
    return gc

def fetch_data_from_query_sheet() -> pd.DataFrame:
    """
    "query_貼付" シートのデータを DataFrame として返す。
    1行目をカラム名、2行目以降をレコードとみなす想定。
    """
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    wks = sh.worksheet(SHEET_NAME)

    all_values = wks.get_all_values()
    if len(all_values) < 2:
        # ヘッダーしかない or シートが空
        return pd.DataFrame()

    header = all_values[0]
    data_rows = all_values[1:]
    df = pd.DataFrame(data_rows, columns=header)
    return df

def main_fetch_all():
    """
    シート 'query_貼付' を取得し、CSVに保存するのみ。
    """
    df = fetch_data_from_query_sheet()
    df.to_csv("sheet_query_data.csv", index=False, encoding="utf-8-sig")
    print("シート 'query_貼付' のデータを 'sheet_query_data.csv' に保存しました。")
