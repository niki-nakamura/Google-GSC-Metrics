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
    - Rewrite Priority Score ボタンで sales=0 を除外し、降順ソート
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
        for c in reversed(actual_new_cols):
            if c in col_list:
                col_list.remove(c)
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
            oldPos = row["30日間平均順位"]
            newPos = row["7日間平均順位"]
            if oldPos > 0:
                return ((oldPos - newPos) / oldPos) * 100
            else:
                return 0
        df["growth_rate"] = df.apply(calc_growth_rate, axis=1)
        df["growth_rate"] = df["growth_rate"].round(1)

    # -------------------------------
    # 6) Rewrite Priority Score ボタン
    # -------------------------------
    st.write("### フィルタ & 拡張機能")
    colA, _ = st.columns([2.5, 7.5])
    with colA:
        rewrite_priority_btn = st.button("Rewrite Priority Scoreで降順ソート")
        st.caption("売上（収益）が発生している記事のみが対象となり、売上、コンバージョン、トラフィック、伸びしろ、検索順位改善の全ての観点から総合的に評価された記事が上位にくる")

    # ---- ここでボタンの処理を実行 (関数内に含める) ----
    if rewrite_priority_btn:
        # (1) sales が 0 の行を除外
        df = df[pd.to_numeric(df["sales"], errors="coerce").fillna(0) > 0]

        # ★ ここで 「30日間平均順位」「7日間平均順位」がどちらも 3.0位以下の行を除外
        if "30日間平均順位" in df.columns and "7日間平均順位" in df.columns:
            # 両方とも <= 3 の行を除外する => (条件式)を反転させて取り除く
            df = df[~((df["30日間平均順位"] <= 3) & (df["7日間平均順位"] <= 3))]

        # (2) 数値化処理
        for cname in ["sales","cv","page_view","imp","growth_rate","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        # (3) 重み付け
        w_sales = 1.0
        w_cv    = 1.0
        w_pv    = 0.5
        w_imp   = 0.5
        w_gr    = 0.3
        w_pos   = 0.2

        def calc_rp(row):
            s   = float(row.get("sales", 0))
            c   = float(row.get("cv", 0))
            pv  = float(row.get("page_view", 0))
            imp = float(row.get("imp", 0))
            gr  = float(row.get("growth_rate", 0))     
            pos = float(row.get("avg_position", 9999))

            score = (np.log(s+1) * w_sales
                    + c * w_cv
                    + np.log(pv+1)* w_pv
                    + np.log(imp+1)* w_imp
                    + gr * w_gr
                    - pos * w_pos)
            return score

        # (4) Rewrite Priority Score 計算・ソート
        df["rewrite_priority"] = df.apply(calc_rp, axis=1)
        df.sort_values("rewrite_priority", ascending=False, inplace=True)

    # -------------------------------
    # 7) 表示用: セル横スクロール対応
    # -------------------------------
    def wrap_cell(val):
        s = str(val)
        s_esc = html.escape(s)
        return f'<div class="cell-content">{s_esc}</div>'

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

## Rewrite Priority Score（リライト優先度）の考え方

「リライトで成果を伸ばしやすい記事」から効率的に着手するために、**売上やCV、アクセス数、検索順位など複数の指標を組み合わせて1つのスコア**に統合しています。  
これにより、単に売上が高い・PVが多いだけでなく、「順位が上がりつつある」「今後さらに伸ばせそう」な記事を総合的に評価できます。

---

## 2. スコアの算出方法

Rewrite Priority Score は、次の式に示すように **対数変換** と **重み付け** を組み合わせた評価指標です。

Rewrite Priority Score  =  (log(sales + 1) * w_sales)
                        + (cv               * w_cv)
                        + (log(page_view+1) * w_pv)
                        + (log(imp + 1)     * w_imp)
                        + (growth_rate      * w_gr)
                        - (avg_position     * w_pos)


### 2-1. 指標ごとの役割

---

### 2-1. 指標ごとの役割（例）

1. **(log(sales + 1) * w_sales)**  
   - **sales**: 過去7日間などの売上金額  
   - **log(x+1)**: 売上が極端に大きい場合の影響を緩和しつつ、売上実績があるほど高評価にするための対数変換  
   - **w_sales**: 「売上」をどれだけ重視するかを示す重み付け値  

2. **(cv * w_cv)**  
   - **cv**: コンバージョン数（問い合わせ、会員登録、アプリDLなど）  
   - **w_cv**: コンバージョンをどれだけ重視するかを示す重み付け値  

3. **(log(page_view + 1) * w_pv)**  
   - **page_view**: 過去7日間のページビュー数  
   - **log(x+1)**: PVが非常に多い記事とそうでない記事の差をならすためのログ圧縮  
   - **w_pv**: PVを評価にどの程度反映させるか  

4. **(log(imp + 1) * w_imp)**  
   - **imp**: 検索インプレッション（検索結果に表示された回数）  
   - **log(x+1)**: 高インプレッションの影響を部分的に平準化  
   - **w_imp**: インプレッションの重要度をコントロールする重み  

5. **(growth_rate * w_gr)**  
   - **growth_rate**: 「30日平均順位 → 7日平均順位」の **順位改善率(%)**  
   - 値が大きいほど「最近順位が上昇傾向」で伸びしろがあると判断  
   - **w_gr**: 順位改善度合いをどれだけ重視するか  

6. **-(avg_position * w_pos)**  
   - **avg_position**: 7日間平均の検索順位（数値が小さいほど上位）  
   - **マイナス要素** として組み込むことで、上位（数値が小さい）ほどスコアが高くなる  
   - **w_pos**: 「平均順位」をどの程度考慮するか  

---

### 2-2. 対数変換（log変換）とは

\(\log(x + 1)\) の形で使われる「対数変換」は、**一部の指標（sales, page_view, imp など）が極端に大きい場合に、スコアが過剰に偏るのを抑える** 役割があります。  
具体的には、売上やPVが桁違いに大きい記事を優遇しすぎないようにしつつも、大きい値の差は一定程度反映されるように調整しています。

---

### 2-3. 重み付け（w_{\mathrm{sales}}, w_{\mathrm{cv}} など）

- **売上やCVをより重視** したい場合は、その重み \(w_{\mathrm{sales}}, w_{\mathrm{cv}}\) を他より大きく設定します。  
- PVやimpは「今後の伸びしろ」を見る指標として中程度の重みにし、  
- 順位（avg_position）は「現在の検索上位度合い」としてマイナス評価を行うことで **高順位（低い値）ほど加点** となります。

たとえば下記のような設定例があります:

- `w_sales = 1.0`  
- `w_cv    = 1.0`  
- `w_pv    = 0.5`  
- `w_imp   = 0.5`  
- `w_gr    = 0.3`  
- `w_pos   = 0.2`  (順位はマイナスで組み込む)

---

### 2-4. このスコアを使うメリット

1. **売上やCVが期待できる記事を優先**  
   - 過去に売上実績がある記事ほど高いスコアになりやすい。  
   - リライトの投下リソースを「稼ぎ頭の改善」に集中させられる。

2. **“あと少しで伸びる記事” を見逃さない**  
   - PVやインプレッションがそれなりにあり、順位改善率が高い記事も上位に来やすいため、**リライトの効果が出やすい** 記事を確実に拾える。

3. **定量データに基づく合理的な判断**  
   - 経験や勘だけではなく、客観的な数値（売上、PV、順位など）を複合的に見て「どの記事を優先すべきか」を判断できる。

---

> **まとめ**  
> Rewrite Priority Score は、**売上・CV** といったビジネス成果の要素を中心に、**アクセス数（PV/imp）** や **順位改善率** などを加えてバランス良くスコア化したものです。  
> これにより「利益に直結しやすい」「成長余地が大きい」記事をハイライトし、リライト施策の優先順位を明確にすることができます。
---

以上が README のリライト内容です。  
**Rewrite Priority Score** は、売上やPVなどの数値データをもとに「リライトで成果を伸ばしやすい順」に並べるための指標です。**“成果に直結しやすい記事”** から優先的に着手することで、限られた時間や人員で最大限のリライト効果を得ることができます。
    """

def show_sheet2():
    st.title("README:")
    st.markdown(README_TEXT)

def streamlit_main():
    tab1, tab2 = st.tabs(["📊 Data Viewer", "📖 README"])
    with tab1:
        show_sheet1()
    with tab2:
        show_sheet2()

if __name__ == "__main__":
    streamlit_main()
