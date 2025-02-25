# streamlit_app.py

import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

def load_data() -> pd.DataFrame:
    """
    main_fetch_all() 実行後に生成される "wp_content_latest.csv" を読み込む。
    """
    try:
        df = pd.read_csv("wp_content_latest.csv")
    except:
        df = pd.DataFrame()  # 空DataFrame
    return df

def streamlit_main():
    st.title("wp_content_by_result_* (直近7日) データ閲覧")

    # データ更新ボタン
    if st.sidebar.button("最新データを取得/更新"):
        with st.spinner("BigQueryから直近7日データを取得中..."):
            main_fetch_all()
        st.sidebar.success("データを更新しました。")

    # CSV読込
    df = load_data()

    if df.empty:
        st.warning("まだデータがありません。サイドバーのボタンを押して取得してください。")
        return

    # テーブル表示
    st.subheader("取得したデータ一覧")
    st.dataframe(df)

    # さらにカラムごとにグラフ化などする例 (任意)
    if "page_view" in df.columns:
        st.subheader("page_view の簡易集計")
        st.bar_chart(df["page_view"])

if __name__ == "__main__":
    streamlit_main()
