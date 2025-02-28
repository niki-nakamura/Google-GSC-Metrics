import streamlit as st
import pandas as pd
import numpy as np
import html
from data_fetcher import main_fetch_all

# ページ全体を横幅を広めに使う
st.set_page_config(layout="wide")

def load_data() -> pd.DataFrame:
    """
    sheet_query_data.csv を読み込んで DataFrame を返す。
    失敗したら空の DataFrame を返す。
    """
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def show_sheet1():
    """
    ● sum_position 列を非表示
    ● page_view合計を小数点第一位
    ● 新規4項目 (SEO対策KW,30日間平均順位,7日間平均順位,比較（7日間が良ければ＋）) を post_title 後ろに挿入
    ● growth_rate ボタンで列を追加
    ● CVR×avg_position ボタンでスコア算出＆降順ソート
    ● 需要(imp)×収益(sales or cv) ボタンで指標算出＆降順ソート
    ● 特定4列( session,30日間平均順位,7日間平均順位,比較 )を狭い列幅にする
    (上記以外は列幅150px)
    """

    # 狭い列にしたいカラム
    NARROW_COLUMNS = {
        "session",
        "30日間平均順位",
        "7日間平均順位",
        "比較（7日間が良ければ＋）"
    }

    # CSS (セル横スクロールはそのまま、列幅固定クラスを追加)
    st.markdown(
        """
        <style>
        /* タイトル/ID の text_input を狭く */
        input[type=text] {
            width: 150px !important;
        }
        /* テーブル全体 */
        table.customtable {
            border-collapse: separate;
            border-spacing: 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            width: 100%;
        }
        /* 角丸 */
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

        /* ヘッダー文字をスクロール可能に */
        table.customtable thead th .header-content {
            display: inline-block;
            max-width: 120px;
            white-space: nowrap;
            overflow-x: auto;
        }

        /* 通常セル（max-width:150px） */
        .cell-default {
            display: inline-block;
            max-width: 150px;
            white-space: nowrap;
            overflow-x: auto;
        }
        /* 狭いセル（max-width:80px） */
        .cell-narrow {
            display: inline-block;
            max-width: 80px;
            white-space: nowrap;
            overflow-x: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("""
    **項目定義**:  
    ID=一意ID, title=記事名, category=分類, CV=コンバージョン, 
    page_view=PV数, URL=リンク先 等
    """)

    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    # 不要な列
    if "ONTENT_TYPE" in df.columns:
        df.drop(columns=["ONTENT_TYPE"], inplace=True)
    if "sum_position" in df.columns:
        df.drop(columns=["sum_position"], inplace=True)

    # 新規4項目を post_title 後ろに
    new_cols = ["SEO対策KW", "30日間平均順位", "7日間平均順位", "比較（7日間が良ければ＋）"]
    actual_new_cols = [c for c in new_cols if c in df.columns]
    if "post_title" in df.columns:
        idx_post_title = df.columns.get_loc("post_title")
        col_list = list(df.columns)
        # 既存位置から4項目を抜く
        for c in actual_new_cols:
            if c in col_list:
                col_list.remove(c)
        # post_title直後に挿入
        for c in reversed(actual_new_cols):
            col_list.insert(idx_post_title+1, c)
        df = df[col_list]

    # 数値列を小数点第1位
    numeric_cols = df.select_dtypes(include=["float","int"]).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # page_view合計
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{round(total_pv,1)}")

    # UI
    st.write("### フィルタ & 拡張機能")
    col1, col2, col3, col4 = st.columns([2.5, 2, 2, 2.5])
    with col1:
        filter_sales_cv = st.checkbox("売上 or CV が 0 以上のみ表示")
    with col2:
        cv_min = st.number_input("最低CV", value=0.0, step=0.5)
    with col3:
        pv_min = st.number_input("最低page_view", value=0.0, step=10.0)
    with col4:
        apply_multi_btn = st.button("Apply 複数条件フィルタ")

    colA, colB, colC, colD, colE = st.columns([2.5, 2, 2, 2, 2.5])
    with colA:
        rewrite_priority_btn = st.button("Rewrite Priority Scoreで降順ソート")
    with colB:
        growth_btn = st.button("伸びしろ( growth_rate )")
    with colC:
        cvravgpos_btn = st.button("CVR × Avg. Position")
    with colD:
        imp_sales_btn = st.button("需要(imp) × 収益(sales or cv)")

    # フィルタ処理
    if filter_sales_cv:
        if "sales" in df.columns:
            df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        if "sales" in df.columns and "cv" in df.columns:
            df = df[(df["sales"] > 0) | (df["cv"] > 0)]
        else:
            st.warning("sales や cv 列が無いためフィルタ不可。")

    if apply_multi_btn:
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        if "page_view" in df.columns:
            df["page_view"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        if "cv" in df.columns and "page_view" in df.columns:
            df = df[(df["cv"] >= cv_min) & (df["page_view"] >= pv_min)]
        else:
            st.warning("cv や page_view 列が無いためフィルタ不可。")

    # Rewrite Priority
    if rewrite_priority_btn:
        for cname in ["sales","cv","page_view","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)
        w_sales = 1.0
        w_cv = 1.0
        w_pv = 0.5
        w_pos= 0.2

        def calc_rp(row):
            s   = max(0, float(row.get("sales",0)))
            c   = max(0, float(row.get("cv",0)))
            pv  = max(0, float(row.get("page_view",0)))
            pos = float(row.get("avg_position",9999))
            return (np.log(s+1)*w_sales
                    + c*w_cv
                    + np.log(pv+1)*w_pv
                    - pos*w_pos)

        df["rewrite_priority"] = df.apply(calc_rp, axis=1)
        df.sort_values("rewrite_priority", ascending=False, inplace=True)

    # 伸びしろ(growth_rate)
    if growth_btn:
        if "page_view" in df.columns:
            df["page_view"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
            df["growth_rate"] = ((df["page_view"] + 1)/(df["page_view"] + 5) - 1)*100
            df["growth_rate"] = df["growth_rate"].round(1)
        else:
            st.warning("page_view 列が無いため growth_rate 計算不可。")

    # CVR×avg_position
    if cvravgpos_btn:
        for cname in ["cv","click","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)
        if not all(x in df.columns for x in ["cv","click","avg_position"]):
            st.warning("cv,click,avg_position が揃ってないため実装不可。")
        else:
            def calc_cvrpos(row):
                cl = float(row["click"])
                c = float(row["cv"])
                pos= float(row["avg_position"])
                if cl<=0:
                    cvr=0
                else:
                    cvr=c/cl
                score= cvr/(pos+1)
                return score
            df["cvravgpos_score"] = df.apply(calc_cvrpos, axis=1)
            df.sort_values("cvravgpos_score", ascending=False, inplace=True)

    # 需要(imp)×収益
    if imp_sales_btn:
        for x in ["imp","sales","cv"]:
            if x in df.columns:
                df[x] = pd.to_numeric(df[x], errors="coerce").fillna(0)
        if "imp" not in df.columns:
            st.warning("imp 列が無いため需要×収益不可。")
        else:
            def calc_imp_rev(row):
                i= float(row["imp"])
                s= float(row.get("sales",0))
                c= float(row.get("cv",0))
                rev= s if s>0 else c
                return i*rev
            df["imp_revenue_score"] = df.apply(calc_imp_rev, axis=1)
            df.sort_values("imp_revenue_score", ascending=False, inplace=True)

    st.write("### query_貼付 シート CSV のビューワー")

    # URL列 (右寄せリンク)
    if "URL" in df.columns:
        def clickable_url(cell):
            c_str= str(cell)
            c_esc= html.escape(c_str)
            if c_str.startswith("http"):
                return f'<div class="cell-content" style="text-align:right;"><a href="{c_esc}" target="_blank">{c_esc}</a></div>'
            else:
                return f'<div class="cell-content" style="text-align:right;">{c_esc}</div>'
        df["URL"] = df["URL"].apply(clickable_url)

    # 特定4列を狭く、それ以外をデフォルト幅
    # 狭くしたい列セット
    narrow_cols = {
        "session",
        "30日間平均順位",
        "7日間平均順位",
        "比較（7日間が良ければ＋）"
    }

    def wrap_cell(val, colname):
        s = str(val)
        s_esc = html.escape(s)
        if colname in narrow_cols:
            # 狭い列
            return f'<div class="cell-content" style="max-width:80px; overflow-x:auto; white-space:nowrap;">{s_esc}</div>'
        else:
            # 通常列 (max-width:150px)
            return f'<div class="cell-content">{s_esc}</div>'

    # URLは既に個別対応済み, 他の列に対して wrap_cell
    for col in df.columns:
        if col.startswith('<div class="header-content">'):
            # これはヘッダーHTML済みなのでスキップ
            continue
        if col!="URL":
            df[col] = df[col].apply(lambda v: wrap_cell(v, col))

    # ヘッダー
    new_header= []
    for c in df.columns:
        c_esc= html.escape(c)
        new_header.append(f'<div class="header-content">{c_esc}</div>')
    df.columns= new_header

    html_table= df.to_html(
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

