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
    - growth_rate を「30日間平均順位」「7日間平均順位」から計算
    - Rewrite Priority Score ボタンで降順ソート（sales, cv, page_view, imp, growth_rate, avg_positionを統合）
    """
    # -------------------------------
    # 1) CSSや前準備部分（テーブルのカスタムCSS）
    # -------------------------------
    st.markdown(
        """
        <style>
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
            max-width: 120px; 
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
    直近7日間の各種指標をBigQueryで集計。
    """)

    # -------------------------------
    # 2) CSVを読み込む
    # -------------------------------
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

    # -------------------------------
    # 3) 数値列の丸め処理
    # -------------------------------
    numeric_cols = df.select_dtypes(include=["float","int"]).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # -------------------------------
    # 4) page_view合計(小数点第1位)を表示
    # -------------------------------
    if "page_view" in df.columns:
        df["page_view_numeric"] = pd.to_numeric(df["page_view"], errors="coerce").fillna(0)
        total_pv = df["page_view_numeric"].sum()
        st.metric("page_view の合計", f"{round(total_pv, 1)}")

    # -------------------------------
    # 5) growth_rate を「30日間平均順位」「7日間平均順位」から計算
    # -------------------------------
    if "30日間平均順位" in df.columns and "7日間平均順位" in df.columns:
        df["30日間平均順位"] = pd.to_numeric(df["30日間平均順位"], errors="coerce").fillna(0)
        df["7日間平均順位"] = pd.to_numeric(df["7日間平均順位"], errors="coerce").fillna(0)

        def calc_growth_rate(row):
            oldPos = row["30日間平均順位"]  # 30日間の平均順位
            newPos = row["7日間平均順位"]   # 7日間の平均順位
            # oldPos > 0 のとき (oldPos - newPos) / oldPos * 100
            # 順位が改善(新Posが小さい)ならプラス、悪化ならマイナス
            if oldPos > 0:
                return ((oldPos - newPos) / oldPos) * 100
            else:
                return 0  # oldPosが0か負なら計算できないので0とする

        df["growth_rate"] = df.apply(calc_growth_rate, axis=1)
        df["growth_rate"] = df["growth_rate"].round(1)

    # -------------------------------
    # 6) Rewrite Priority Score ボタン
    # -------------------------------
    st.write("### フィルタ & 拡張機能")
    colA, _ = st.columns([2.5, 7.5])
    with colA:
        rewrite_priority_btn = st.button("Rewrite Priority Scoreで降順ソート")
        st.caption("sales, cv, page_view, imp, growth_rate, avg_position などを統合した優先度")

    if rewrite_priority_btn:
        # 対象の各列を数値化（欠損時は0）
        for cname in ["sales","cv","page_view","imp","growth_rate","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        # 重み付け（必要に応じて調整可能）
        w_sales = 1.0    # 売上
        w_cv    = 1.0    # CV
        w_pv    = 0.5    # page_view
        w_imp   = 0.5    # imp（インプレッション）
        w_gr    = 0.3    # growth_rate（順位改善度合い）
        w_pos   = 0.2    # avg_position（大きいほどマイナス評価）

        def calc_rp(row):
            s   = float(row.get("sales", 0))
            c   = float(row.get("cv", 0))
            pv  = float(row.get("page_view", 0))
            imp = float(row.get("imp", 0))
            gr  = float(row.get("growth_rate", 0))     
            pos = float(row.get("avg_position", 9999))

            # ログ変換等でスケール調整
            score = (np.log(s+1) * w_sales
                     + c           * w_cv
                     + np.log(pv+1)* w_pv
                     + np.log(imp+1)* w_imp
                     + gr          * w_gr
                     - pos         * w_pos)
            return score

        df["rewrite_priority"] = df.apply(calc_rp, axis=1)
        df.sort_values("rewrite_priority", ascending=False, inplace=True)

    # -------------------------------
    # 7) 表示用: セル横スクロール対応
    # -------------------------------
    def wrap_cell(val):
        s = str(val)
        s_esc = html.escape(s)
        return f'<div class="cell-content">{s_esc}</div>'

    # URL列のみ右寄せ＋クリック対応
    if "URL" in df.columns:
        def clickable_url(cell):
            cell_str = str(cell)
            if cell_str.startswith("http"):
                esc = html.escape(cell_str)
                return f'<div class="cell-content" style="text-align:right;"><a href="{esc}" target="_blank">{esc}</a></div>'
            else:
                return f'<div class="cell-content" style="text-align:right;">{html.escape(cell_str)}</div>'
        df["URL"] = df["URL"].apply(clickable_url)

    for col in df.columns:
        if col != "URL":
            df[col] = df[col].apply(wrap_cell)

    # ヘッダーにも横スクロール用のラッパーを適用
    new_cols = []
    for c in df.columns:
        c_esc = html.escape(c)
        new_cols.append(f'<div class="header-content">{c_esc}</div>')
    df.columns = new_cols

    # -------------------------------
    # 8) HTMLテーブルに変換して表示
    # -------------------------------
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
