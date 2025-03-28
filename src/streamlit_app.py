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
    - growth_rate（順位改善率）の計算
    - Rewrite Priority Score ボタン（sales=0除外 + 降順ソート）
    - Ahrefs風デザイン＆UI
    - 表示列の順番もAhrefs風に揃える
    """

    # -------------------------------
    # 1) テーブルのカスタムCSS + sorttable.js + UIヘッダー情報
    # -------------------------------
    st.markdown(
        """
        <!-- sorttable.js (列ヘッダクリックでソート可能にする) -->
        <script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>

        <style>
        /* テーブル全体をAhrefs風にアップグレード */
        table.ahrefs-table {
            border-collapse: separate;
            border-spacing: 0;
            border: 1px solid #ddd;
            border-radius: 8px; /* 角丸を少し大きく */
            overflow: hidden;
            width: 100%;
            font-family: "Arial", sans-serif;
            font-size: 14px;
        }

        /* ヘッダー部分 */
        table.ahrefs-table thead tr {
            background-color: #f9f9f9; /* 少し明るめ */
        }
        table.ahrefs-table thead th {
            font-weight: bold;
            padding: 8px;
            border-bottom: 1px solid #ddd;
            white-space: nowrap;
        }

        /* 角丸設定 */
        table.ahrefs-table thead tr:first-child th:first-child {
            border-top-left-radius: 8px;
        }
        table.ahrefs-table thead tr:first-child th:last-child {
            border-top-right-radius: 8px;
        }
        table.ahrefs-table tbody tr:last-child td:first-child {
            border-bottom-left-radius: 8px;
        }
        table.ahrefs-table tbody tr:last-child td:last-child {
            border-bottom-right-radius: 8px;
        }

        /* ボディ部分 */
        table.ahrefs-table tbody tr td {
            padding: 6px 8px;
            border-bottom: 1px solid #eee; 
            white-space: nowrap;
            vertical-align: middle;
        }

        /* ホバー時の色付け */
        table.ahrefs-table tbody tr:hover {
            background-color: #fefefe;
        }

        /* ソートできるテーブルのヘッダにはカーソルを指マークに */
        table.sortable thead {
            cursor: pointer;
        }

        /* ヘッダー部分のセルも nowrap + 横スクロール可能に */
        table.ahrefs-table thead th .header-content {
            display: inline-block;
            max-width: 120px;
            white-space: nowrap;
            overflow-x: auto;
        }

        /* 本文セルの中身を横スクロール許可 */
        table.ahrefs-table td .cell-content {
            display: inline-block;
            max-width: 180px; /* 少し広めに */
            white-space: nowrap;
            overflow-x: auto;
        }

        /* URLセルを右寄せにして省略する例 */
        .url-cell {
            max-width: 260px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            text-align: right;
            display: inline-block;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ここでは例として「667 ページ」「合計トラフィック : 173.5K」「日付選択UI」などをあらかじめ書いておきます
    st.subheader("667 ページ　合計トラフィック : 173.5K")
    st.caption("2025年3月28日 vs. 2025年3月20日")

    # -------------------------------
    # 2) CSVを読み込む + 前処理
    # -------------------------------
    df = load_data()
    if df.empty:
        st.warning("まだデータがありません。CSVが空か、データ取得がまだかもしれません。")
        return

    # 不要な列の除去
    if "ONTENT_TYPE" in df.columns:
        df.drop(columns=["ONTENT_TYPE"], inplace=True)
    if "sum_position" in df.columns:
        df.drop(columns=["sum_position"], inplace=True)

    # 例: growth_rate が必要な場合（順位の改善率）
    if "30日間平均順位" in df.columns and "7日間平均順位" in df.columns:
        df["30日間平均順位"] = pd.to_numeric(df["30日間平均順位"], errors="coerce").fillna(0)
        df["7日間平均順位"] = pd.to_numeric(df["7日間平均順位"], errors="coerce").fillna(0)
        def calc_growth_rate(row):
            old_pos = row["30日間平均順位"]
            new_pos = row["7日間平均順位"]
            if old_pos > 0:
                return round(((old_pos - new_pos) / old_pos) * 100, 1)
            return 0.0
        df["growth_rate"] = df.apply(calc_growth_rate, axis=1)

    # 数値列の丸め
    numeric_cols = df.select_dtypes(include=["float","int"]).columns
    df[numeric_cols] = df[numeric_cols].round(1)

    # -------------------------------
    # 3) Rewrite Priority Score ボタン + フィルタ
    # -------------------------------
    st.write("### フィルタ & 拡張機能")
    colA, _ = st.columns([2.5, 7.5])
    with colA:
        rewrite_priority_btn = st.button("Rewrite Priority Score で降順ソート")
        st.caption("売上（収益）が発生している記事のみが対象となり、売上・CV・トラフィック・伸びしろ・検索順位などを総合評価し、優先度を算出")

    if rewrite_priority_btn:
        # sales=0 を除外
        df = df[pd.to_numeric(df.get("sales", 0), errors="coerce").fillna(0) > 0]

        # 30日間平均順位 & 7日間平均順位 がどちらも <=3 の場合を除外
        if {"30日間平均順位", "7日間平均順位"}.issubset(df.columns):
            df = df[~((df["30日間平均順位"] <= 3) & (df["7日間平均順位"] <= 3))]

        # 数値化
        for cname in ["sales", "cv", "page_view", "imp", "growth_rate", "avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        # スコア計算
        w_sales = 1.0
        w_cv    = 1.0
        w_pv    = 0.5
        w_imp   = 0.5
        w_gr    = 0.3
        w_pos   = 0.2

        def calc_rp(row):
            s   = row.get("sales", 0)
            c   = row.get("cv", 0)
            pv  = row.get("page_view", 0)
            imp = row.get("imp", 0)
            gr  = row.get("growth_rate", 0)
            pos = row.get("avg_position", 9999)
            score = (np.log(s+1)*w_sales
                     + c*w_cv
                     + np.log(pv+1)*w_pv
                     + np.log(imp+1)*w_imp
                     + gr*w_gr
                     - pos*w_pos)
            return score

        df["rewrite_priority"] = df.apply(calc_rp, axis=1).round(1)
        df.sort_values("rewrite_priority", ascending=False, inplace=True)

    # -------------------------------
    # 4) 表示順をAhrefs風に揃える（例）
    # -------------------------------
    # 例: 「URL」「ステータス」「トラフィック」「変更」... の順に並べる
    desired_order = [
        "URL",           # 例: ページURL
        "ステータス",      # 例: 9,426 5.4%
        "トラフィック",      # 例: 9426
        "変更",           # 例: -1.8K
        "値",            # 例: $2.7K
        "変更(値)",       # 例: -$509
        "キーワード",       # 例: 2,516
        "変更(KW)",       # 例: -1.3K
        "トップキーワード",  # 例: ポイ活 おすすめ
        "ボリューム",       # 例: 45.0K
        "順位",           # 例: 7
        "コンテンツの変更",   # 例: 大 or 小
        "検査"            # 例: 🔍(虫メガネ)
    ]
    # CSVに本当にある列だけを抽出
    existing_cols = [c for c in desired_order if c in df.columns]
    df = df[existing_cols] if existing_cols else df

    # -------------------------------
    # 5) セルのHTML整形 (URLを右寄せ + リンク化、その他はスクロールWrap)
    # -------------------------------
    def wrap_cell(val):
        s = str(val)
        s_esc = html.escape(s)
        return f'<div class="cell-content">{s_esc}</div>'

    if "URL" in df.columns:
        def make_clickable_url(url_val):
            s_esc = html.escape(str(url_val))
            return f'<div class="url-cell"><a href="{s_esc}" target="_blank">{s_esc}</a></div>'
        df["URL"] = df["URL"].apply(make_clickable_url)

    # その他の列をラップ
    for col in df.columns:
        if col != "URL":  # URLはすでに整形済み
            df[col] = df[col].apply(wrap_cell)

    # ヘッダに <div class="header-content"> を付与
    new_cols = []
    for c in df.columns:
        c_esc = html.escape(c)
        new_cols.append(f'<div class="header-content">{c_esc}</div>')
    df.columns = new_cols

    # -------------------------------
    # 6) HTMLテーブル化 (sortable)
    # -------------------------------
    html_table = df.to_html(
        escape=False,
        index=False,
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
        show_sheet1()
    with tab2:
        show_sheet2()

if __name__ == "__main__":
    streamlit_main()
