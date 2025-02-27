import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

# ページ全体をワイド表示に設定
st.set_page_config(layout="wide")

def load_data() -> pd.DataFrame:
    """CSV を読み込む。ない場合は空DataFrameを返す"""
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def streamlit_main():
    # 一番上に各項目の定義を書いておく
    st.markdown("""
    ## 項目の定義
    - **CV** : コンバージョン（アプリのダウンロード数 等）
    """)

    # データをロード
    df = load_data()

    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    # 数値列を小数点以下1桁で丸める（適宜調整）
    # ただし、混合データの場合はエラーにならないようにする
    numeric_cols = df.select_dtypes(include=['float','int']).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # page_viewの合計を先に表示
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{total_pv}")

    # 検索ボックス: タイトル検索
    title_search = st.text_input("タイトル検索（部分一致）")
    if title_search:
        if "title" in df.columns:
            df = df[df["title"].astype(str).str.contains(title_search, na=False)]

    # 検索ボックス: ID検索
    id_search = st.text_input("ID検索（部分一致）")
    if id_search:
        if "id" in df.columns:
            df = df[df["id"].astype(str).str.contains(id_search, na=False)]

    # categoryでプルダウンフィルタ
    if "category" in df.columns:
        category_list = df["category"].dropna().unique().tolist()
        category_selected = st.selectbox("category を絞り込み", ["すべて"] + category_list)
        if category_selected != "すべて":
            df = df[df["category"] == category_selected]

    # URL列をクリック可能にする例
    if "URL" in df.columns:
        def make_clickable(url):
            url = str(url)
            if url.startswith("http"):
                return f'<a href="{url}" target="_blank">{url}</a>'
            else:
                return url
        df["URL"] = df["URL"].apply(make_clickable)

    # 列幅を抑えるCSS（必要に応じて微調整）
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

    # HTML形式で表示することで、URLリンクをクリック可能に
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

if __name__ == "__main__":
    streamlit_main()
