import streamlit as st
import pandas as pd
import numpy as np
from data_fetcher import main_fetch_all

# Configure the page layout in wide mode for more horizontal space
st.set_page_config(layout="wide")

###################################
# Sheet1: CSV Viewer
###################################

def load_data() -> pd.DataFrame:
    """
    Attempts to read the CSV file 'sheet_query_data.csv'.
    If reading fails, returns an empty DataFrame instead.
    """
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def show_sheet1():
    """
    Main function for displaying the CSV data plus
    our new horizontal arrangement of filters and buttons.
    """

    # Inject custom CSS to style the table (rounded corners, etc.)
    st.markdown(
        """
        <style>
        /* Make text inputs (for title/ID, etc.) narrower */
        input[type=text] {
            width: 150px !important;
        }

        /* HTML table styling: border, rounding, etc. */
        table.customtable {
            border-collapse: separate;
            border-spacing: 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden; /* keeps corners actually rounded */
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
            max-width: 150px; 
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # A short explanation of key columns (unchanged).
    st.markdown("""
    **項目定義**: 
    ID=一意ID, title=記事名, category=分類, CV=コンバージョン, 
    page_view=PV数, URL=リンク先 等
    """)

    # 1) Load data from CSV
    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    # 2) Remove 'ONTENT_TYPE' if it exists
    if "ONTENT_TYPE" in df.columns:
        df.drop(columns=["ONTENT_TYPE"], inplace=True)

    # 3) Round numeric columns to one decimal
    numeric_cols = df.select_dtypes(include=["float", "int"]).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # 4) If page_view column is present, compute total and show a metric
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{total_pv}")

    # ---------------------
    # Place our filter & extension features HORIZONTALLY
    # We'll do multiple columns, so they appear side-by-side
    # ---------------------
    st.write("### フィルタ & 拡張機能")

    # Row 1: 
    #   - (col1) A checkbox for "売上 or CV > 0"
    #   - (col2) "最低CV" input
    #   - (col3) "最低page_view" input
    #   - (col4) Button to apply the multiple filter
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns([2, 2, 2, 2])

    # A) Checkbox: sales or cv > 0
    with row1_col1:
        filter_sales_cv = st.checkbox("売上 or CV が 0 以上の記事のみ表示")

    # B) Numeric inputs for multiple-condition filter
    with row1_col2:
        cv_min = st.number_input("最低CV", value=0.0, step=0.5)
    with row1_col3:
        pv_min = st.number_input("最低page_view", value=0.0, step=10.0)
    with row1_col4:
        # We'll hold the button for applying these filters
        apply_multi_btn = st.button("Apply 複数条件フィルタ")

    # Row 2:
    #   - (colA) Rewrite Priority Score button
    #   - (colB) 伸びしろ(growth_rate)
    #   - (colC) CVR × Avg.Position
    #   - (colD) imp × sales
    row2_colA, row2_colB, row2_colC, row2_colD = st.columns([2, 2, 2, 2])

    with row2_colA:
        rewrite_priority_btn = st.button("Rewrite Priority Scoreで降順ソート")
    with row2_colB:
        growth_btn = st.button("伸びしろ( growth_rate )")
    with row2_colC:
        cvr_btn = st.button("CVR × Avg. Position")
    with row2_colD:
        imp_sales_btn = st.button("需要(imp) × 収益(sales or cv)")

    # ---------- Actually apply the filters & button logic now -------------
    # 1) Filter for sales > 0 or cv > 0 if checkbox is set
    if filter_sales_cv:
        # Convert columns to numeric if they exist
        if "sales" in df.columns:
            df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        # Filter only if both columns exist
        if "sales" in df.columns and "cv" in df.columns:
            df = df[(df["sales"] > 0) | (df["cv"] > 0)]
        else:
            st.warning("sales or cv 列が見つからないため、フィルタを適用できません。")

    # 2) If the "Apply 複数条件フィルタ" button was clicked
    if apply_multi_btn:
        # Convert to numeric safely
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        if "page_view" in df.columns:
            df["page_view"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)

        # Check and apply
        if "cv" in df.columns and "page_view" in df.columns:
            df = df[(df["cv"] >= cv_min) & (df["page_view"] >= pv_min)]
        else:
            st.warning("cv or page_view 列が見つからないため、フィルタを適用できません。")

    # 3) Rewrite Priority Score if button pressed
    if rewrite_priority_btn:
        w_sales = 1.0
        w_cv = 1.0
        w_pv = 0.5
        w_pos = 0.2

        def calc_rewrite_priority(row):
            """
            Combine multiple factors (sales, cv, page_view, avg_position)
            into a single numeric priority score. 
            Higher => higher rewrite priority.
            """
            # Safely parse columns
            s = float(row.get("sales", 0) or 0)
            c = float(row.get("cv", 0) or 0)
            pv = float(row.get("page_view", 0) or 0)
            pos = float(row.get("avg_position", 9999) or 9999)

            # Example formula using ln to soften big values
            s_term = np.log(s + 1) * w_sales
            c_term = c * w_cv
            pv_term = np.log(pv + 1) * w_pv
            pos_term = -pos * w_pos  # smaller pos => better => negative factor
            return s_term + c_term + pv_term + pos_term

        # Add new column and sort descending
        df["rewrite_priority"] = df.apply(calc_rewrite_priority, axis=1)
        df.sort_values("rewrite_priority", ascending=False, inplace=True)

    # 4) Placeholder button logic for the others
    if growth_btn:
        st.info("今後: growth_rate で上昇/下降を判定するロジックを追加予定")

    if cvr_btn:
        st.info("CVR が高い＆avg_position が3~10位の記事を抽出する機能を今後実装")

    if imp_sales_btn:
        st.info("今後、imp×sales でポテンシャルを評価する指標を導入予定")

    # Show the CSV viewer heading
    st.write("### query_貼付 シート CSV のビューワー")

    # Make URL column clickable & right-aligned if present
    if "URL" in df.columns:
        def make_clickable(url):
            url = str(url)
            if url.startswith("http"):
                return f'<div style="text-align:right;"><a href="{url}" target="_blank">{url}</a></div>'
            else:
                return f'<div style="text-align:right;">{url}</div>'
        df["URL"] = df["URL"].apply(make_clickable)

    # Convert the DataFrame to HTML for display
    html_table = df.to_html(
        escape=False,
        index=False,
        classes=["customtable"]
    )
    st.write(html_table, unsafe_allow_html=True)


###################################
# (Hidden) README doc
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
    st.title("README:")
    st.markdown(README_TEXT)

def streamlit_main():
    # タブ2枚
    tab1, tab2 = st.tabs(["📊 Data Viewer", "📖 README"])
    with tab1:
        show_sheet1()
    with tab2:
        show_sheet2()

if __name__ == "__main__":
    streamlit_main()
