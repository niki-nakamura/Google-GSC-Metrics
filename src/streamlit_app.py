# streamlit_app.py
import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

def load_data() -> pd.DataFrame:
    """
    main_fetch_all() 実行後に生成される "sheet_query_data.csv" を読み込む。
    """
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def streamlit_main():
    st.title("query_貼付 シート データ閲覧")

    # データ更新ボタン
    if st.sidebar.button("最新データを取得/更新"):
        with st.spinner("Google Sheets 'query_貼付' からデータを取得中..."):
            main_fetch_all()  # シート読み込み→CSV保存
        st.sidebar.success("データを更新しました！")

    # CSV読込
    df = load_data()

    if df.empty:
        st.warning("まだデータがありません。左サイドバーからデータを取得してください。")
        return

    st.subheader("query_貼付 シート → CSV のプレビュー")
    st.dataframe(df)

    # 例: カラム "page_view" があれば合計を表示
    if "page_view" in df.columns:
        st.subheader("page_view の合計")
        # 数値変換
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.write(f"合計: {total_pv}")

if __name__ == "__main__":
    streamlit_main()
