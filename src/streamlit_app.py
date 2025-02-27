import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

# ページ全体をワイド表示に
st.set_page_config(layout="wide")

def load_data() -> pd.DataFrame:
    """CSV を読み込む。ない場合は空DataFrameを返す"""
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def streamlit_main():
    # 全体用のCSS: テキストボックスを最小幅にする
    st.markdown(
        """
        <style>
        /* タイトル検索/ID検索のテキストボックスを狭く */
        input[type=text] {
            width: 150px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 一番上に項目の定義
    st.markdown("""
    ## 項目の定義
    - **CV** : コンバージョン（アプリのダウンロード数 等）
    """)

    # CSV データ読み込み
    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    # 数値列を小数点以下1桁に丸める
    numeric_cols = df.select_dtypes(include=['float','int']).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # page_view の合計を上部に表示
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{total_pv}")

    # カテゴリをカンマ分割してリスト化（「ツール,広告ブロック」を ["ツール", "広告ブロック"] に）
    unique_cats = []
    if "category" in df.columns:
        df["split_categories"] = df["category"].fillna("").apply(
            lambda x: [c.strip() for c in x.split(",") if c.strip()]
        )
        # プルダウン用の全カテゴリの集合を作る
        cat_set = set()
        for cats in df["split_categories"]:
            cat_set.update(cats)
        unique_cats = sorted(cat_set)

    # 横に3つのカラムを配置 (タイトル検索、ID検索、カテゴリ選択)
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        title_search = st.text_input("タイトル検索（部分一致）")
    with col2:
        id_search = st.text_input("ID検索（部分一致）")
    with col3:
        if len(unique_cats) > 0:
            category_selected = st.selectbox("category を絞り込み", ["すべて"] + unique_cats)
        else:
            category_selected = "すべて"

    # フィルタ1: タイトル検索
    if title_search and "title" in df.columns:
        df = df[df["title"].astype(str).str.contains(title_search, na=False)]

    # フィルタ2: ID検索
    if id_search and "id" in df.columns:
        df = df[df["id"].astype(str).str.contains(id_search, na=False)]

    # フィルタ3: カテゴリ選択
    if category_selected != "すべて" and "split_categories" in df.columns:
        df = df[df["split_categories"].apply(lambda catlist: category_selected in catlist)]

    st.write("### query_貼付 シート CSV のビューワー")

    # 元のst.dataframeのスタイルに戻す + 高さ大きめ指定
    st.dataframe(df, use_container_width=True, height=1200)

if __name__ == "__main__":
    streamlit_main()
