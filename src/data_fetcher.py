import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def main_fetch_all():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json',  # サービスアカウントJSONファイル
        scope
    )
    client = gspread.authorize(creds)

    SPREADSHEET_KEY = '1jnxiqozvo5EQa30Yl-Tk9AH-raMsnpCPGsQ_C2io4Ik'
    SHEET_NAME = 'query_貼付'

    sh = client.open_by_key(SPREADSHEET_KEY)
    worksheet = sh.worksheet(SHEET_NAME)

    data = worksheet.get_all_values()

    if not data:  # シートが空の場合
        df = pd.DataFrame()
    else:
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)

    # CSV 出力
    df.to_csv("sheet_query_data.csv", index=False, encoding="utf-8-sig")
    print("Data has been fetched from Sheets and saved to sheet_query_data.csv!")

if __name__ == "__main__":
    main_fetch_all()
