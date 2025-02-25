# data_fetcher.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def main_fetch_all():
    """
    Google Sheets 'query_貼付' シートから最新データを取得し、
    'sheet_query_data.csv' というCSVに書き出す。
    """

    # 1) 認証設定
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json',  # サービスアカウントJSONファイル
        scope
    )
    client = gspread.authorize(creds)

    # 2) スプレッドシートを開く
    #    SPREADSHEET_KEY はURLの「/d/」と「/edit」間にある部分
    SPREADSHEET_KEY = '1jnxiqozvo5EQa30Yl-Tk9AH-raMsnpCPGsQ_C2io4Ik'
    SHEET_NAME = 'query_貼付'

    sh = client.open_by_key(SPREADSHEET_KEY)
    worksheet = sh.worksheet(SHEET_NAME)

    # 3) シート全体の値を取得して pandas.DataFrame に変換
    data = worksheet.get_all_values()
    if not data:
        df = pd.DataFrame()
    else:
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)

    # 4) CSVに書き出し
    df.to_csv("sheet_query_data.csv", index=False, encoding="utf-8-sig")
    print("Data has been fetched from Sheets and saved to sheet_query_data.csv!")
