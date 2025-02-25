# streamlit_app.py

import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

def load_data() -> pd.DataFrame:
    """
    main_fetch_all() 実行後に生成される "sheet_query_data.csv" を読み込む。
    """
    try:
        df = pd.read_csv("sheet_query_data.csv")
    except:
        df = pd.DataFrame()
    return df

def streamlit_main():
    st.title("query_貼付 シートデータのStreamlit表示")

    if st.sidebar.button("最新データを取得/更新"):
        with st.spinner("GoogleSheets 'query_貼付' からデータ取得中..."):
            main_fetch_all()  # シート読み込み→CSV保存
        st.sidebar.success("データを更新しました。")

    # CSV読込
    df = load_data()

    if df.empty:
        st.warning("まだデータがありません。サイドバーのボタンを押して取得してください。")
        return

    st.subheader("query_貼付 シート内容 (CSV) のプレビュー")
    st.dataframe(df)

    # カラム例: event_date, CONTENT_TYPE, POST_ID, etc...
    # 必要に応じて集計・可視化
    if "page_view" in df.columns:
        st.subheader("page_view の合計:")
        total_pv = pd.to_numeric(df["page_view"], errors="coerce").sum()
        st.write(f"合計: {total_pv}")

        st.subheader("page_view の簡易グラフ")
        # 数値型でないとグラフが描けないため convert
        numeric_df = df[["page_view"]].apply(pd.to_numeric, errors="coerce").fillna(0)
        st.bar_chart(numeric_df["page_view"])

if __name__ == "__main__":
    streamlit_main()
