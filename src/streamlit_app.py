import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

# ページ全体をワイド表示に
st.set_page_config(layout="wide")

# ここに README の文章をベタ書き (もしくは別ファイルなどでもOK)
README_TEXT = """
# README: 直近7日間の「column」記事データ集計クエリ

## 概要
- **目的**  
  - WordPress 投稿のうち、`CONTENT_TYPE = 'column'` である記事を対象に、直近7日間の各種指標（セッション・PV・クリックなど）を BigQuery 上で集計する。
  - 併せて、WordPress DB から記事の「カテゴリー情報」を取得・紐づけし、1つのテーブルとして出力する。

... (中略) ...

## 出力カラムについて
| カラム名  | 役割・意味                                                     |
|-----------|----------------------------------------------------------------|
| CONTENT_TYPE     | 記事種別（今回は固定で `column`）。                |
| POST_ID          | WordPress の投稿ID。                             |
| URL              | 対象記事のURL。                            |
| category         | 記事に紐づくカテゴリー（カンマ区切り）。           |
| post_title       | 投稿タイトル。                                   |
| session          | セッション数の平均（直近7日）。                  |
| page_view        | ページビュー数の平均（直近7日）。                |
| click_app_store  | アプリストアへのリンククリック数の平均。         |
| ...             | ... (以下省略) ...

以上がクエリ全体のREADMEです。必要に応じて社内で加筆・修正してください。
"""

def load_data() -> pd.DataFrame:
    """CSV を読み込む。ない場合は空DataFrameを返す"""
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def show_data_viewer():
    # 従来の「query_貼付 シート CSV ビューワー」表示ロジック
    st.title("📈 G!A SEO指標 with Streamlit")

    st.markdown(
        """
        <style>
        /* ... CSS部分は同じ ... */
        table.customtable {
            border-collapse: separate;
            border-spacing: 0;
            ...
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("""
    **項目定義**: ID=一意ID, title=記事名, category=分類, CV=コンバージョン, page_view=PV数, URL=リンク先 等
    """)

    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    if "ONTENT_TYPE" in df.columns:
        df.drop(columns=["ONTENT_TYPE"], inplace=True)

    # 数値列を小数点以下1桁に丸める
    numeric_cols = df.select_dtypes(include=['float','int']).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # page_view の合計を表示
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{total_pv}")

    # カテゴリ絞り込み等は略
    st.write("### query_貼付 シート CSV のビューワー")

    # URLの右寄せリンク化例
    if "URL" in df.columns:
        def make_clickable(url):
            url = str(url)
            if url.startswith("http"):
                return f'<div style=\"text-align:right;\"><a href=\"{url}\" target=\"_blank\">{url}</a></div>'
            else:
                return f'<div style=\"text-align:right;\">{url}</div>'
        df["URL"] = df["URL"].apply(make_clickable)

    html_table = df.to_html(escape=False, index=False, classes=["customtable"])
    st.write(html_table, unsafe_allow_html=True)


def show_readme():
    # README シート内容の表示
    st.title("README シート")
    st.markdown(README_TEXT)

def streamlit_main():
    # タブを使って画面を切り替え
    tab1, tab2 = st.tabs(["📊 Data Viewer", "📖 README"])

    with tab1:
        show_data_viewer()
    with tab2:
        show_readme()

if __name__ == "__main__":
    streamlit_main()
