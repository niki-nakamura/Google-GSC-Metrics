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
    - growth_rate ボタンで計算列を追加
    - CVR×avg_position ボタンで cv / click & その結果を avg_position と組み合わせた指標でソート
    - 需要(imp) × 収益(sales or cv) ボタンで指標計算し、降順ソート
    """

    # CSS: stickyヘッダを使わずにセル横スクロールを実装中のCSS
    st.markdown(
        """
        <style>
        /* タイトル/ID 用の text_input を狭く */
        input[type=text] {
            width: 150px !important;
        }

        /* テーブル全体のデザイン */
        table.customtable {
            border-collapse: separate;
            border-spacing: 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            width: 100%;
        }
        /* 角丸設定 */
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

        /* ヘッダー部分のセルも nowrap + 横スクロール可能に */
        table.customtable thead th .header-content {
            display: inline-block;
            max-width: 120px;      /* 列幅固定の目安 */
            white-space: nowrap;   
            overflow-x: auto;      
        }

        /* 本文セルの中身を横スクロール許可 */
        table.customtable td .cell-content {
            display: inline-block;
            max-width: 150px;
            white-space: nowrap;
            overflow-x: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("""
    **項目定義**:  
    ID=一意ID, title=記事名, category=分類, CV=コンバージョン, page_view=PV数, URL=リンク先 等
    """)

    # CSVを読み込む
    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    # 不要な列削除
    if "ONTENT_TYPE" in df.columns:
        df.drop(columns=["ONTENT_TYPE"], inplace=True)
    if "sum_position" in df.columns:
        df.drop(columns=["sum_position"], inplace=True)

    # 新規4項目を post_title の直後に挿入
    new_cols = ["SEO対策KW", "30日間平均順位", "7日間平均順位", "比較（7日間が良ければ＋）"]
    actual_new_cols = [c for c in new_cols if c in df.columns]
    if "post_title" in df.columns:
        idx = df.columns.get_loc("post_title")
        col_list = list(df.columns)
        for c in actual_new_cols:
            if c in col_list:
                col_list.remove(c)
        for c in reversed(actual_new_cols):
            col_list.insert(idx+1, c)
        df = df[col_list]

    # 数値列を小数点1桁で丸める
    numeric_cols = df.select_dtypes(include=["float","int"]).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # page_view合計(小数点第1位)
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{round(total_pv, 1)}")

    st.write("### フィルタ & 拡張機能")

    # 上段
    col1, col2, col3, col4 = st.columns([2.5, 2, 2, 2.5])
    with col1:
        filter_sales_cv = st.checkbox("売上 or CV が 0 以上のみ表示")
    with col2:
        cv_min = st.number_input("最低CV", value=0.0, step=0.5)
    with col3:
        pv_min = st.number_input("最低page_view", value=0.0, step=10.0)
    with col4:
        apply_multi_btn = st.button("Apply 複数条件フィルタ")

    # 下段
    colA, colB, colC, colD, colE = st.columns([2.5, 2, 2, 2, 2.5])
    with colA:
        rewrite_priority_btn = st.button("Rewrite Priority Scoreで降順ソート")
    with colB:
        growth_btn = st.button("伸びしろ( growth_rate )")
    with colC:
        cvravgpos_btn = st.button("CVR × Avg. Position")
    with colD:
        imp_sales_btn = st.button("需要(imp) × 収益(sales or cv)")
    # colE はスペーサー or 追加余地

    # ------ フィルタ ------
    if filter_sales_cv:
        # sales, cv を数値化
        if "sales" in df.columns:
            df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        if "sales" in df.columns and "cv" in df.columns:
            df = df[(df["sales"] > 0) | (df["cv"] > 0)]
        else:
            st.warning("sales や cv 列が無いのでフィルタできません。")

    if apply_multi_btn:
        if "cv" in df.columns:
            df["cv"] = pd.to_numeric(df["cv"], errors="coerce").fillna(0)
        if "page_view" in df.columns:
            df["page_view"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        if "cv" in df.columns and "page_view" in df.columns:
            df = df[(df["cv"] >= cv_min) & (df["page_view"] >= pv_min)]
        else:
            st.warning("cv や page_view 列が無いのでフィルタできません。")

    # Rewrite Priority
    if rewrite_priority_btn:
        for cname in ["sales","cv","page_view","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        w_sales = 1.0
        w_cv    = 1.0
        w_pv    = 0.5
        w_pos   = 0.2

        def calc_rp(row):
            s   = max(0, float(row.get("sales", 0)))
            c   = max(0, float(row.get("cv", 0)))
            pv  = max(0, float(row.get("page_view", 0)))
            pos = float(row.get("avg_position",9999))
            return (np.log(s+1)*w_sales
                    + c*w_cv
                    + np.log(pv+1)*w_pv
                    - pos*w_pos)

        df["rewrite_priority"] = df.apply(calc_rp, axis=1)
        df.sort_values("rewrite_priority", ascending=False, inplace=True)

    # 伸びしろ (growth_rate)
    if growth_btn:
        if "page_view" in df.columns:
            df["page_view"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
            df["growth_rate"] = ((df["page_view"] + 1)/(df["page_view"] + 5) - 1)*100
            df["growth_rate"] = df["growth_rate"].round(1)
        else:
            st.warning("page_view 列が無いため growth_rate 計算不可。")

    # (1) CVR×avg_position の実装
    # クリック数(click)とcvがあれば CVR = cv / click(0除外)
    # それを avg_position と組み合わせた指標で降順ソート
    if cvravgpos_btn:
        # 必要なカラムを数値化
        for cname in ["cv","click","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        # カラムが無ければ中断
        if not all(col in df.columns for col in ["cv","click","avg_position"]):
            st.warning("cv, click, avg_position のいずれかが無いため実装不可。")
        else:
            def calc_cvrpos(row):
                cl = float(row["click"])
                c = float(row["cv"])
                pos = float(row["avg_position"])
                if cl <= 0:
                    cvr = 0
                else:
                    cvr = c/cl
                # 例: cvr / (pos+1) でスコア化
                score = cvr / (pos+1)
                return score
            df["cvravgpos_score"] = df.apply(calc_cvrpos, axis=1)
            df.sort_values("cvravgpos_score", ascending=False, inplace=True)

    # (2) 需要(imp) × 収益(sales or cv)
    # sales>0 があれば imp*sales、なければ imp*cv などの方針
    if imp_sales_btn:
        # imp, sales, cv を数値化
        for cname in ["imp","sales","cv"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        if "imp" not in df.columns:
            st.warning("imp 列が無いため需要(imp)×収益 計算不可。")
        else:
            def calc_imp_revenue(row):
                impv = float(row["imp"])
                s = float(row.get("sales",0))
                c = float(row.get("cv",0))
                # sales があればそちらを優先
                revenue = s if s>0 else c
                return impv * revenue
            df["imp_revenue_score"] = df.apply(calc_imp_revenue, axis=1)
            df.sort_values("imp_revenue_score", ascending=False, inplace=True)

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

    # ヘッダー（th）にも横スクロール部品
    new_cols = []
    for c in df.columns:
        c_esc = html.escape(c)
        new_cols.append(f'<div class="header-content">{c_esc}</div>')
    df.columns = new_cols

    # HTMLテーブル出力
    html_table = df.to_html(
        escape=False,  
        index=False,
        classes=["customtable"]
    )
    st.write(html_table, unsafe_allow_html=True)

###################################
# (Hidden) README doc
###################################

README_TEXT = """\
# 直近7日間の「column」記事データ集計クエリ

## 概要
- **目的**  
  - WordPress 投稿のうち `CONTENT_TYPE = 'column'` である記事を対象に、**直近7日間**の各種指標（セッション数、PV数、クリックなど）をBigQueryで集計。
  - WordPress DBから記事の「カテゴリー情報」「SEO対策KW」などを取得・紐づけし、1つのテーブルとして出力。

- **出力結果**  
  - 直近7日間の平均を主とする複数指標（session, page_view, sales, cv等）や、30日間平均順位と7日間平均順位などの検索順位情報を付与。
  - 「比較（7日間が良ければ＋）」で順位改善/悪化を確認。
  - データはCSV出力され、Streamlitアプリでフィルタ・ソート可能。

## テーブル構成・主なカラム
| カラム名                       | 役割・意味                                      |
|-------------------------------|-------------------------------------------------|
| POST_ID                       | WordPressの投稿ID                               |
| URL                           | 記事URL (`https://.../column/POST_ID`)         |
| category                      | カテゴリー名(カンマ区切り)                      |
| post_title                    | 記事タイトル                                   |
| SEO対策KW                     | 主となるSEOキーワード                           |
| 30日間平均順位               | 過去30日間の平均検索順位                        |
| 7日間平均順位                | 過去7日間の平均検索順位                         |
| 比較（7日間が良ければ＋）     | (7日間平均順位 - 30日間平均順位) 正の値で改善   |
| session                       | 7日間平均セッション数                          |
| page_view                     | 7日間平均ページビュー                           |
| sales                         | 7日平均売上 (アフィリエイトなど)               |
| cv                            | 7日平均コンバージョン                           |
| click                         | 検索クリック数(7日平均)                         |
| imp                           | 検索インプレッション(7日平均)                  |
| avg_position                  | 検索順位(7日平均)                              |
| growth_rate                   | 伸びしろ(ダミー計算)                            |
| rewrite_priority              | リライト優先度スコア                            |
| cvravgpos_score               | CVR×Avg.Positionスコア                          |
| imp_revenue_score             | 需要(imp)×収益(sales or cv)                    |

## Streamlitアプリでの機能

1. **売上 or CV > 0** のみ表示  
2. **複数条件フィルタ** (CV ≥ X & page_view ≥ Y)  
3. **Rewrite Priority Score** (sales,cv,page_view,avg_positionで優先度算出)  
4. **伸びしろ(growth_rate)** (ダミー式)  
5. **CVR × Avg.Position** (cv/clickをavg_positionと組み合わせてスコア化)  
6. **需要(imp) × 収益(sales or cv)** (impとsales/cvを掛け算)  
7. セル横スクロール・URL右寄せなどUX改善

## データ取得範囲
```sql
DECLARE DS_START_DATE STRING DEFAULT FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY));
DECLARE DS_END_DATE   STRING DEFAULT FORMAT_DATE('%Y%m%d', CURRENT_DATE());
    """


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
