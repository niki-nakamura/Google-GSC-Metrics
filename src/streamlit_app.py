import streamlit as st
import pandas as pd
import numpy as np
import html
from data_fetcher import main_fetch_all

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
    Ahrefs「上位ページ」風に表示する関数。
    - URL
    - SEOタイトル (post_title)
    - トラフィック (page_view_7d)
    - 変更 (traffic_change_7d_vs_30d)
    - 値 (sales_7d)
    - 変更 (sales_7d vs sales_30d)
    - トップキーワード (SEO対策KW)
    - 順位 (7日間平均順位)

    そのほかのカラムは右側へ置く。
    """

    # --------------------------------------------------
    # 1) CSS + sorttable.js
    # --------------------------------------------------
    st.markdown(
        """
        <script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
        <style>
        table.ahrefs-table {
            border-collapse: separate;
            border-spacing: 0;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
            width: 100%;
            font-family: "Arial", sans-serif;
            font-size: 14px;
            background-color: #fff;
        }
        table.ahrefs-table thead tr {
            background-color: #f7f7f7;
        }
        table.ahrefs-table thead th {
            font-weight: bold;
            padding: 8px;
            border-bottom: 1px solid #ddd;
            white-space: nowrap;
        }
        table.ahrefs-table thead tr:first-child th:first-child {
            border-top-left-radius: 6px;
        }
        table.ahrefs-table thead tr:first-child th:last-child {
            border-top-right-radius: 6px;
        }
        table.ahrefs-table tbody tr:last-child td:first-child {
            border-bottom-left-radius: 6px;
        }
        table.ahrefs-table tbody tr:last-child td:last-child {
            border-bottom-right-radius: 6px;
        }
        table.ahrefs-table tbody tr td {
            padding: 6px 8px;
            border-bottom: 1px solid #ddd;
            white-space: nowrap;
            vertical-align: middle;
            transition: background-color 0.3s;
        }
        table.ahrefs-table tbody tr:hover {
            background-color: #fafafa;
        }
        table.sortable thead {
            cursor: pointer;
        }
        table.ahrefs-table thead th .header-content {
            display: inline-block;
            max-width: 120px;
            white-space: nowrap;
            overflow-x: auto;
        }
        table.ahrefs-table td .cell-content {
            display: inline-block;
            max-width: 150px;
            white-space: nowrap;
            overflow-x: auto;
        }
        .pos-change { color: green; }
        .neg-change { color: red; }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.subheader("Ahrefs風 上位ページ")

    # --------------------------------------------------
    # 2) CSV読み込み
    # --------------------------------------------------
    df = load_data()
    if df.empty:
        st.warning("CSVが空、またはまだデータがありません。")
        return

    # --------------------------------------------------
    # 3) カラム名のリネーム
    # --------------------------------------------------
    rename_map = {
        "SEO対策KW": "keyword_top",
        "7日間平均順位": "rank_7d",
        "sales_7d": "sales_7d",
        "sales_30d": "sales_30d",
        "sales_change_7d_vs_30d": "sales_change",
        "page_view_7d": "traffic_7d",
        "traffic_change_7d_vs_30d": "traffic_change",
        "post_title": "seo_title",
        # URL はそのまま
    }
    for oldcol, newcol in rename_map.items():
        if oldcol in df.columns:
            df.rename(columns={oldcol: newcol}, inplace=True)

    # --------------------------------------------------
    # 4) URLをクリック可能に
    # --------------------------------------------------
    if "URL" in df.columns:
        def make_clickable(u):
            esc = html.escape(str(u))
            return f'<div class="cell-content"><a href="{esc}" target="_blank">{esc}</a></div>'
        df["URL"] = df["URL"].apply(make_clickable)

    # --------------------------------------------------
    # 5) 表示順を Ahrefs 風に
    # --------------------------------------------------
    desired_cols = [
        "URL",
        "seo_title",
        "traffic_7d",
        "traffic_change",
        "sales_7d",
        "sales_change",
        "keyword_top",
        "rank_7d"
    ]
    exist_cols = [c for c in desired_cols if c in df.columns]
    others = [c for c in df.columns if c not in exist_cols]
    final_cols = exist_cols + others
    df = df[final_cols]

    # --------------------------------------------------
    # 6) プラス・マイナス値の色付け
    # --------------------------------------------------
    def color_change(val):
        s = str(val)
        try:
            x = float(val)
            if x > 0:
                return f'<div class="cell-content pos-change">+{x}</div>'
            elif x < 0:
                return f'<div class="cell-content neg-change">{x}</div>'
            else:
                return f'<div class="cell-content">{x}</div>'
        except:
            return f'<div class="cell-content">{html.escape(s)}</div>'

    for colnm in ["traffic_change", "sales_change"]:
        if colnm in df.columns:
            df[colnm] = df[colnm].apply(color_change)

    # --------------------------------------------------
    # 7) 他の列をスクロール対応HTML化
    # --------------------------------------------------
    def wrap_cell(v):
        return f'<div class="cell-content">{html.escape(str(v))}</div>'

    for c in df.columns:
        if (c not in ["URL","traffic_change","sales_change"]) and (c in df.columns):
            df[c] = df[c].apply(wrap_cell)

    # --------------------------------------------------
    # 8) ヘッダを <div class=\"header-content\"> でラップ
    # --------------------------------------------------
    new_headers = []
    for col in df.columns:
        # 既に <div class=\"cell-content\"> が入ってしまっている場合は削除
        text = col.replace('<div class=\"cell-content\">','').replace('</div>','')
        new_headers.append(f'<div class="header-content">{html.escape(text)}</div>')
    df.columns = new_headers

    # --------------------------------------------------
    # 9) HTMLテーブル化して表示
    # --------------------------------------------------
    html_table = df.to_html(
        index=False,
        escape=False,
        classes=["ahrefs-table", "sortable"]
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
   - **growth_rate**: 「30日間平均順位 → 7日間平均順位」の **順位改善率(%)**  
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
        # ここで show_sheet1() を呼ぶように
        show_sheet1()
    with tab2:
        show_sheet2()

if __name__ == "__main__":
    streamlit_main()
