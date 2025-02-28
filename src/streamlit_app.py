import streamlit as st
import pandas as pd
import numpy as np
import html
from data_fetcher import main_fetch_all

# ページ全体を横幅を広めに使う設定
st.set_page_config(layout="wide")

def load_data() -> pd.DataFrame:
    """
    sheet_query_data.csv を読み込み、失敗したら空DataFrameを返す。
    """
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def show_sheet1():
    """
    CSVを読み込んで表示する。
    - sum_position 列を非表示
    - page_view合計を小数点第一位
    - 新規4項目を post_title の直後に挿入
    - 列ヘッダーとセルを一行化し、長い場合は横スクロールできるようにする
    - growth_rate ボタンで計算列を追加
    """

    # CSS: テーブルの角丸、ヘッダ・セルのスクロール設定など
    st.markdown(
        """
        <style>
/* 表全体をブロック要素化し、縦スクロールできるように */
table.customtable {
    display: block;               /* ブロック要素として扱う */
    max-height: 600px;           /* 表示エリアの高さを仮に600pxに制限 */
    overflow-y: auto;            /* 縦スクロールバーを出す */
    border-collapse: separate;
    border-spacing: 0;
    border: 1px solid #ddd;
    border-radius: 8px;
    width: 100%;
}

/* thead と tbody それぞれをテーブル扱いにして幅を合わせる */
table.customtable thead,
table.customtable tbody {
    display: table;
    width: 100%;
    table-layout: fixed; /* 固定レイアウトでセル幅を揃える */
}

/* 角丸が崩れる場合、個別に指定し直す場合もある */
/* 位置がずれる可能性があるため、見た目を微調整してください */

/* ヘッダーのセルを上端に固定 */
table.customtable thead th {
    position: sticky;      /* スクロールしても固定 */
    top: 0;                /* ページ最上部を基準に固定 */
    background-color: #fff;/* 背景色を付けてスクロール時に判別しやすく */
    z-index: 2;            /* 本文セルより前面に出す */
    white-space: nowrap;   /* ヘッダー文字を一行で表示 */
    overflow-x: auto;      /* はみ出す場合に横スクロール */
}

/* セル内部の横スクロール等は、以前と同じ設定でOK */
table.customtable thead th .header-content {
    display: inline-block;
    max-width: 120px;
    white-space: nowrap;
    overflow-x: auto;
}

table.customtable tbody td .cell-content {
    display: inline-block;
    max-width: 150px;
    white-space: nowrap;
    overflow-x: auto;
}

        </style>
        """,
        unsafe_allow_html=True
    )

    # 項目定義の簡易説明
    st.markdown("""
    **項目定義**:  
    ID=一意ID, title=記事名, category=分類, CV=コンバージョン, page_view=PV数, URL=リンク先 等
    """)

    # CSV読み込み
    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    # 不要な列を消す
    if "ONTENT_TYPE" in df.columns:
        df.drop(columns=["ONTENT_TYPE"], inplace=True)
    if "sum_position" in df.columns:
        df.drop(columns=["sum_position"], inplace=True)

    # 例: 新規4項目を post_title の後ろに並べる
    new_cols = ["SEO対策KW", "30日間平均順位", "7日間平均順位", "比較（7日間が良ければ＋）"]
    actual_new_cols = [c for c in new_cols if c in df.columns]
    if "post_title" in df.columns:
        idx_post_title = df.columns.get_loc("post_title")
        # まず new_cols を削除しておく（既存順序から外す）
        col_list = list(df.columns)
        for c in actual_new_cols:
            if c in col_list:
                col_list.remove(c)
        # post_title の直後に挿入
        for c in reversed(actual_new_cols):
            col_list.insert(idx_post_title+1, c)
        df = df[col_list]

    # 数値列を小数点以下1桁に丸める
    numeric_cols = df.select_dtypes(include=["float","int"]).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # page_view合計を小数点第一位で表示
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{round(total_pv, 1)}")

    st.write("### フィルタ & 拡張機能")

    # 1行目
    col1, col2, col3, col4 = st.columns([2.5, 2, 2, 2.5])
    with col1:
        filter_sales_cv = st.checkbox("売上 or CV が 0 以上のみ表示")
    with col2:
        cv_min = st.number_input("最低CV", value=0.0, step=0.5)
    with col3:
        pv_min = st.number_input("最低page_view", value=0.0, step=10.0)
    with col4:
        apply_multi_btn = st.button("Apply 複数条件フィルタ")

    # 2行目
    colA, colB, colC, colD = st.columns([2.5, 2, 2, 2.5])
    with colA:
        rewrite_priority_btn = st.button("Rewrite Priority Scoreで降順ソート")
    with colB:
        growth_btn = st.button("伸びしろ( growth_rate )")
    with colC:
        cvr_btn = st.button("CVR × Avg. Position")
    with colD:
        imp_sales_btn = st.button("需要(imp) × 収益(sales or cv)")

    # ------ フィルタロジック ------
    if filter_sales_cv:
        if "sales" in df.columns:
            df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        if "sales" in df.columns and "cv" in df.columns:
            df = df[(df["sales"] > 0) | (df["cv"] > 0)]
        else:
            st.warning("sales や cv 列が無いためフィルタできません。")

    if apply_multi_btn:
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        if "page_view" in df.columns:
            df["page_view"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        if "cv" in df.columns and "page_view" in df.columns:
            df = df[(df["cv"] >= cv_min) & (df["page_view"] >= pv_min)]
        else:
            st.warning("cv や page_view 列が無いためフィルタできません。")

    # Rewrite Priority スコア計算
    if rewrite_priority_btn:
        for cname in ["sales","cv","page_view","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        w_sales = 1.0
        w_cv    = 1.0
        w_pv    = 0.5
        w_pos   = 0.2

        def calc_rewrite_priority(row):
            s   = max(0, float(row.get("sales", 0)))
            c   = max(0, float(row.get("cv", 0)))
            pv  = max(0, float(row.get("page_view", 0)))
            pos = float(row.get("avg_position",9999))
            s_term = np.log(s+1)*w_sales
            c_term = c*w_cv
            pv_term = np.log(pv+1)*w_pv
            pos_term = -pos*w_pos
            return s_term + c_term + pv_term + pos_term

        df["rewrite_priority"] = df.apply(calc_rewrite_priority, axis=1)
        df.sort_values("rewrite_priority", ascending=False, inplace=True)

    # growth_rate ダミー計算
    if growth_btn:
        if "page_view" in df.columns:
            df["page_view"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
            df["growth_rate"] = ((df["page_view"] + 1) / (df["page_view"] + 5) - 1) * 100
            df["growth_rate"] = df["growth_rate"].round(1)
        else:
            st.warning("page_view が無いので growth_rate を計算できません。")

    if cvr_btn:
        st.info("CVR×avg_position の抽出機能は今後実装予定。")

    if imp_sales_btn:
        st.info("imp×sales 等でポテンシャル評価する機能を今後追加予定。")

    st.write("### query_貼付 シート CSV のビューワー")

    # ---------------------------
    # セル表示の横スクロール対応
    # ---------------------------
    def wrap_cell(val):
        """セルの内容を横スクロール可能にする"""
        s = str(val)
        # HTMLエスケープ
        s_esc = html.escape(s)
        return f'<div class="cell-content">{s_esc}</div>'

    # URL列だけは右寄せクリック対応
    if "URL" in df.columns:
        def clickable_url(cell):
            cell_str = str(cell)
            if cell_str.startswith("http"):
                cell_esc = html.escape(cell_str)
                return f'<div class="cell-content" style="text-align:right;"><a href="{cell_esc}" target="_blank">{cell_esc}</a></div>'
            else:
                return f'<div class="cell-content" style="text-align:right;">{html.escape(cell_str)}</div>'
        df["URL"] = df["URL"].apply(clickable_url)

    # 他の列は wrap_cell で処理
    for col in df.columns:
        if col != "URL":
            df[col] = df[col].apply(wrap_cell)

    # ---------------------------
    # ヘッダー（th）にも横スクロールを仕込む
    # ---------------------------
    # 既存の列名に <div class="header-content"> を包む
    new_cols = []
    for c in df.columns:
        c_esc = html.escape(c)
        new_cols.append(f'<div class="header-content">{c_esc}</div>')
    df.columns = new_cols

    # HTMLテーブル出力
    html_table = df.to_html(
        escape=False,  # wrap済みなのでエスケープは不要
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
    """README用タブ"""
    st.title("README:")
    st.markdown(README_TEXT)

def streamlit_main():
    """タブを2つ用意して表示。"""
    tab1, tab2 = st.tabs(["📊 Data Viewer", "📖 README"])
    with tab1:
        show_sheet1()
    with tab2:
        show_sheet2()

if __name__ == "__main__":
    streamlit_main()

