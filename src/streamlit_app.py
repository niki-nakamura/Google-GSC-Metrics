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
        input[type=text] {
            width: 150px !important; /* タイトル検索/ID検索のテキストボックスを狭く */
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

    # タイトル検索（部分一致）
    title_search = st.text_input("タイトル検索（部分一致）")
    if title_search and "title" in df.columns:
        df = df[df["title"].astype(str).str.contains(title_search, na=False)]

    # ID検索（部分一致）
    id_search = st.text_input("ID検索（部分一致）")
    if id_search and "id" in df.columns:
        df = df[df["id"].astype(str).str.contains(id_search, na=False)]

    # category分割: カンマ区切りを分離して複数カテゴリ扱いに
    if "category" in df.columns:
        # 「ツール,広告ブロック」→ ["ツール", "広告ブロック"] のように分割
        df["split_categories"] = df["category"].fillna("").apply(
            lambda x: [c.strip() for c in x.split(",") if c.strip()]
        )
        # 全行のカテゴリをまとめて集合化 -> プルダウン候補
        unique_cats = set()
        for cats in df["split_categories"]:
            unique_cats.update(cats)
        unique_cats = sorted(unique_cats)  # ソートしておく
        category_selected = st.selectbox("category を絞り込み", ["すべて"] + unique_cats)

        # 「すべて」以外が選ばれたら、そのカテゴリを含む行を抽出
        if category_selected != "すべて":
            df = df[df["split_categories"].apply(lambda catlist: category_selected in catlist)]

    # URL列をリンク化
    if "URL" in df.columns:
        def make_clickable(url):
            url = str(url)
            if url.startswith("http"):
                return f'<a href="{url}" target="_blank">{url}</a>'
            else:
                return url
        df["URL"] = df["URL"].apply(make_clickable)

    # 表示用のCSS: 列幅を狭め、テキストを省略表示
    st.markdown(
        """
        <style>
        table.dataframe td, table.dataframe th {
            max-width: 150px;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.write("### query_貼付 シート CSV のビューワー")

    # HTMLテーブルで表示 (URLクリック可能)
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

if __name__ == "__main__":
    streamlit_main()
