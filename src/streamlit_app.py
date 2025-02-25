import streamlit as st
import pandas as pd
import numpy as np
from data_fetcher import main_fetch_all

# 例: Google Spreadsheet連携するなら gspread を使うなど
#import gspread
#from google.oauth2.service_account import Credentials

def load_data():
    """
    事前に data_fetcher.py の main_fetch_all() などを呼び出して
    CSV等にまとめたデータを読み込む想定。
    あるいは直接 fetch_gsc_data() を呼び出すことも可能ですが、
    毎回APIを叩くと遅い場合があります。
    """
    try:
        df = pd.read_csv("merged_data.csv")
    except:
        df = pd.DataFrame(columns=["query","page","clicks","impressions","ctr","position"])
    return df

def streamlit_main():
    st.title("G!A SEO指標：リライト優先管理ツール")

    # サイドバーなどに「データ更新ボタン」
    if st.sidebar.button("最新APIデータを取得/更新"):
        with st.spinner("データ取得中..."):
            main_fetch_all()  # BigQuery, GSC, GA4などをまとめて取得
        st.sidebar.success("データを更新しました。")

    # データロード
    df = load_data()

    # カラム例: [キーワード, URL, 直近の順位, 変動差分, クリック数, ... , リライトステータス]
    # ここでは仮に df に "rewrite_priority" (数値が大きいほど優先度高) と "rewrite_done" (True/False) があると仮定
    if "rewrite_priority" not in df.columns:
        df["rewrite_priority"] = np.random.randint(1, 6, size=len(df))  # ダミー
    if "rewrite_done" not in df.columns:
        df["rewrite_done"] = False

    # リライト優先度のソート
    sort_order = st.selectbox("ソート順", ["優先度が高い順", "優先度が低い順"], index=0)
    ascending = True if sort_order == "優先度が低い順" else False
    df_sorted = df.sort_values("rewrite_priority", ascending=ascending)

    st.subheader("KW一覧 (リライト優先度ソート済)")
    st.dataframe(df_sorted.reset_index(drop=True))

    st.markdown("---")
    st.subheader("リライト状況の更新")

    # 書き換え対象を選ぶ
    selected_row = st.selectbox(
        "リライト状況を更新するKWを選択",
        df_sorted["query"]
    )
    # 選択された行を抽出
    row_data = df_sorted[df_sorted["query"] == selected_row].iloc[0]

    st.write(f"キーワード: {row_data['query']}")
    st.write(f"URL: {row_data['page']}")
    st.write(f"現在のリライト優先度: {row_data['rewrite_priority']}")
    st.write(f"現在のリライト状況: {'済' if row_data['rewrite_done'] else '未'}")

    # 状況更新ボタン
    if st.button("リライト済みにする"):
        # 実際には df を更新 → GoogleSpreadsheetやBigQueryに書き戻す処理が必要
        idx = df_sorted[df_sorted["query"] == selected_row].index
        df.loc[idx, "rewrite_done"] = True

        # ここでスプレッドシート/DBに反映する例：
        # gs = gspread.authorize( your_credentials )
        # wks = gs.open_by_key('your_spreadsheet_id').worksheet('SEO指標')
        # 該当セルを特定→ update_cells() など
        # あるいは BigQuery UPDATE文を流す

        st.success(f"『{selected_row}』をリライト済みに更新しました。")
    
    st.markdown("---")
    st.write("© 2025 Good-Apps.jp など")

if __name__ == "__main__":
    streamlit_main()

