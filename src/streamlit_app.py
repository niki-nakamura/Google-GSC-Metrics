import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

def load_data() -> pd.DataFrame:
    """CSV を読み込む。ない場合は空DataFrameを返す"""
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def streamlit_main():
    st.title("query_貼付 シート データ閲覧")

    # 左サイドバーに「最新データを取得/更新」ボタンを配置
    if st.sidebar.button("最新データを取得/更新"):
        with st.spinner("Google Sheets 'query_貼付' からデータを取得中..."):
            main_fetch_all()  # シート読み込み -> CSV書き出し
        st.sidebar.success("データを更新しました！")

    # CSV をロード
    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。左サイドバーからデータを取得してください。")
        return

    st.subheader("query_貼付 シート CSV のビューワー")
    st.dataframe(df)

    # 例: カラム "page_view" がある場合のみ合計を表示
    if "page_view" in df.columns:
        st.subheader("page_view の合計")
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.write(f"合計PV: {total_pv}")

if __name__ == "__main__":
    streamlit_main()

