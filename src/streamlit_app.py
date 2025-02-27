import streamlit as st
import pandas as pd
from data_fetcher import main_fetch_all

# ページ全体をワイド表示に
st.set_page_config(layout="wide")

###################################
# Sheet1: CSV Viewer
###################################

def load_data() -> pd.DataFrame:
    """CSV を読み込む。ない場合は空DataFrameを返す"""
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def show_sheet1():
    st.markdown(
        """
        <style>
        /* タイトル検索/ID検索のテキストボックスを狭く */
        input[type=text] {
            width: 150px !important;
        }

        /* HTMLテーブルの角丸・枠線などのスタイル */
        table.customtable {
            border-collapse: separate;
            border-spacing: 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden; /* 角丸を適用するため */
            width: 100%;
        }
        table.customtable thead tr:first-child th:first-child {
            border-top-left-radius: 8px;
        }
        table.customtable thead tr:first-child th:last-child {
            border-top-right-radius: 8px;
        }
        table.customtable tbody tr:last-child td:first-child {
            border-bottom-left-radius: 8px;
        }
        table.customtable tbody tr:last-child td:last-child {
            border-bottom-right-radius: 8px;
        }

        table.customtable td, table.customtable th {
            padding: 6px 8px;
            max-width: 150px;       /* 必要に応じて幅を固定 */
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
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

    # 列 "ONTENT_TYPE" を表示しない（あれば削除）
    if "ONTENT_TYPE" in df.columns:
        df.drop(columns=["ONTENT_TYPE"], inplace=True)

    # 数値列を小数点以下1桁に丸める
    numeric_cols = df.select_dtypes(include=['float','int']).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # page_view の合計を上部に表示
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{total_pv}")

    # カテゴリ分割
    unique_cats = []
    if "category" in df.columns:
        df["split_categories"] = df["category"].fillna("").apply(
            lambda x: [c.strip() for c in x.split(",") if c.strip()]
        )
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

    # URLをクリック可能に (HTMLリンク化)、右詰めで表示
    if "URL" in df.columns:
        def make_clickable(url):
            url = str(url)
            if url.startswith("http"):
                return f'<div style="text-align:right;"><a href="{url}" target="_blank">{url}</a></div>'
            else:
                return f'<div style="text-align:right;">{url}</div>'
        df["URL"] = df["URL"].apply(make_clickable)

    # HTMLテーブルとして表示 (角丸CSS適用)
    html_table = df.to_html(
        escape=False,
        index=False,
        classes=["customtable"]
    )
    st.write(html_table, unsafe_allow_html=True)

###################################
# ここから下は「表示したくない」READMEなどを
# コード内に残しておくだけ
###################################

README_TEXT = """

## 直近7日間の「column」記事データ集計クエリ

### 出力カラムについて

| カラム名  | 役割・意味                                                     |
|-----------|----------------------------------------------------------------|
| A_col (CONTENT_TYPE)     | 記事種別（今回は固定で `column`）。                |
| B_col (POST_ID)          | WordPress の投稿ID。                             |
| URL                      | 対象記事のURL。<br>`https://good-apps.jp/media/column/ + post_id`  |
| C_col (cats)             | 記事に紐づくカテゴリー（カンマ区切り）。           |
| D_col (post_title)       | 投稿タイトル。                                   |
| E_col (session)          | セッション数の平均（直近7日）。                  |
| F_col (page_view)        | ページビュー数の平均（直近7日）。                |
| G_col (click_app_store)  | アプリストアへのリンククリック数の平均。         |
| H_col (imp)              | 検索インプレッション数の平均。                   |
| I_col (click)            | 検索クリック数の平均。                           |
| J_col (sum_position)     | 検索結果の合計順位（直近7日の平均）。            |
| K_col (avg_position)     | 検索結果の平均順位（直近7日の平均）。            |
| L_col (sales)            | 売上（アフィリエイトなどの想定、直近7日の平均）。 |
| M_col (app_link_click)   | アプリリンクへのクリック数の平均。               |
| N_col (cv)               | コンバージョン数の平均。                         |

> **補足**：  
> - `J_col (sum_position)` と `K_col (avg_position)` は検索データの取得元によっては意味合いが異なるケースもあります。<br>
>   ここではあくまで BigQuery 内のデータフィールドに紐づく値をそのまま利用しています。  
> - `AVG(...)` で単純平均を取っているため、**累積値ではなく日平均**である点に注意してください。  
> - テーブル名・カラム名は社内データ基盤の命名に合わせています。

### 概要
- **目的**  
  - WordPress 投稿のうち、`CONTENT_TYPE = 'column'` である記事を対象に、直近7日間の各種指標（セッション・PV・クリックなど）を BigQuery 上で集計する。
  - 併せて、WordPress DB から記事の「カテゴリー情報」を取得・紐づけし、1つのテーブルとして出力する。

- **出力結果**  
  - 直近7日間の以下の主な指標を**平均値**としてまとめる。
    - `session`, `page_view`, `click_app_store`, `imp` (インプレッション), `click` (クリック数),  
      `sum_position` (検索結果ポジションの合計), `avg_position` (検索結果ポジションの平均),  
      `sales`, `app_link_click`, `cv` など。  
  - WordPress の投稿ID・タイトル・カテゴリーを紐づけて、記事単位で出力。
  - 最終的には `page_view` の降順（多い順）にソートされた形で取得。

### データ取得範囲
```sql
DECLARE DS_START_DATE STRING DEFAULT FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY));
DECLARE DS_END_DATE   STRING DEFAULT FORMAT_DATE('%Y%m%d', CURRENT_DATE());
```
- `DS_START_DATE`：今日の日付から7日前  
- `DS_END_DATE`：今日の日付  
- `wp_content_by_result_*` という日別のパーティション/サフィックス付きテーブルに対して、上記日付範囲 (`_TABLE_SUFFIX BETWEEN DS_START_DATE AND DS_END_DATE`) でのデータを対象にする。

### クエリの構成

#### 1. カテゴリー情報の取得（`post_cats` CTE）
```sql
WITH post_cats AS (
  SELECT
    CAST(post_id AS STRING) AS post_id,
    STRING_AGG(name, ', ')  AS cats
  ...
)
```
- WordPress DB (MySQL) に対して `EXTERNAL_QUERY` を使い、  
  - `wp_term_relationships` (投稿とタクソノミーの紐付け)  
  - `wp_term_taxonomy` (各タクソノミーの term_id や taxonomy 種類)  
  - `wp_terms` (term_id と実際の名前)  
  を JOIN して**カテゴリー名**を取得。  
- ひとつの記事に複数カテゴリーがある場合は `STRING_AGG` でカンマ区切りにまとめる。

#### 2. メインデータの集計（`main_data` CTE）
```sql
main_data AS (
  SELECT
    CONTENT_TYPE,
    CAST(POST_ID AS STRING)  AS POST_ID,
    ANY_VALUE(post_title)    AS post_title,
    AVG(session)             AS session,
    AVG(page_view)           AS page_view,
    ...
  FROM `afmedia.seo_bizdev.wp_content_by_result_*`
  WHERE
    _TABLE_SUFFIX BETWEEN DS_START_DATE AND DS_END_DATE
    AND CONTENT_TYPE = 'column'
  GROUP BY
    CONTENT_TYPE,
    POST_ID
)
```
- BigQuery 上の `wp_content_by_result_*` テーブル群（日別）から、直近7日間かつ `CONTENT_TYPE='column'` のデータを取得。  
- 記事単位(`POST_ID`)でグルーピングし、**1日ごとの値の平均**を計算。  
- 取得している主な指標は以下：
  - `session`：記事セッション数
  - `page_view`：PV数
  - `click_app_store`：アプリストアへのクリック数
  - `imp`：検索インプレッション
  - `click`：検索クリック数
  - `sum_position`：検索順位(合計)
  - `avg_position`：検索順位(平均)
  - `sales`：売上(関連アフィリエイトなどの概念があれば想定)
  - `app_link_click`：特定アプリへのリンククリック数
  - `cv`：コンバージョン（CV数）

#### 3. 結合・最終SELECT
```sql
SELECT
  m.CONTENT_TYPE      AS A_col,
  m.POST_ID           AS B_col,
  CONCAT('https://good-apps.jp/media/column/', m.POST_ID) AS URL,
  c.cats              AS C_col,
  m.post_title        AS D_col,
  m.session           AS E_col,
  ...
FROM main_data m
LEFT JOIN post_cats c USING (post_id)
ORDER BY m.page_view DESC;
```
- `main_data` と `post_cats` を `post_id` で LEFT JOIN し、投稿のカテゴリー情報を付与する。  
- URL は `post_id` を末尾につけて生成。  
- **ページビュー数の多い順**でソートして結果を表示。

---

以上がクエリ全体のREADMEです。実行時には日付指定部分が自動計算されるため、**“直近7日間のデータを集計して取得”** という形になります。必要に応じて日付範囲を変更したい場合は、`DS_START_DATE` と `DS_END_DATE` の計算ロジックを修正してください。\n"""

def show_sheet2():
    st.title("### README:")
    st.markdown(README_TEXT)


def streamlit_main():
    # 2つのタブを用意
    tab1, tab2 = st.tabs(["📊 Data Viewer", "📖 README"])

    with tab1:
        show_sheet1()
    with tab2:
        show_sheet2()

if __name__ == "__main__":
    streamlit_main()
