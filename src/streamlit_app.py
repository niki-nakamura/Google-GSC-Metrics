import re
import streamlit as st
import pandas as pd
import numpy as np
import html
from data_fetcher import main_fetch_all

st.set_page_config(layout="wide")

# ▼▼▼ ソート状態管理 (変更なし) ▼▼▼
if "traffic_sort_state" not in st.session_state:
    st.session_state["traffic_sort_state"] = 0  # 0:元表示 1:降順 2:昇順
if "sales_sort_state" not in st.session_state:
    st.session_state["sales_sort_state"] = 0
if "rank_sort_state" not in st.session_state:
    st.session_state["rank_sort_state"] = 0

# ▼▼▼ 追加: フィルタ状態管理 ▼▼▼
if "sales_decrease_filter" not in st.session_state:
    st.session_state["sales_decrease_filter"] = False
if "rank_decrease_filter" not in st.session_state:
    st.session_state["rank_decrease_filter"] = False
if "rank_10_30_filter" not in st.session_state:
    st.session_state["rank_10_30_filter"] = False
if "old_update_filter" not in st.session_state:
    st.session_state["old_update_filter"] = False

def load_data() -> pd.DataFrame:
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def show_sheet1():
    """
    表の形式は一切変更せず、ヘッダのoverflow + color分けを再適用。
    """

    st.subheader("上位ページ")

    # ▼▼▼ ここに4つのフィルタボタンを新規追加 ▼▼▼
    fc1, fc2, fc3, fc4 = st.columns([1,1,1,1])
    with fc1:
        if st.button("売上減少"):
            # トグル
            st.session_state["sales_decrease_filter"] = not st.session_state["sales_decrease_filter"]
            # 他はオフにしても良い(同時併用しない場合) ※必要に応じてコメントアウトしてください
            st.session_state["rank_decrease_filter"] = False
            st.session_state["rank_10_30_filter"] = False
            st.session_state["old_update_filter"] = False
    with fc2:
        if st.button("順位減少"):
            st.session_state["rank_decrease_filter"] = not st.session_state["rank_decrease_filter"]
            st.session_state["sales_decrease_filter"] = False
            st.session_state["rank_10_30_filter"] = False
            st.session_state["old_update_filter"] = False
    with fc3:
        if st.button("順位10-30＋"):
            st.session_state["rank_10_30_filter"] = not st.session_state["rank_10_30_filter"]
            st.session_state["sales_decrease_filter"] = False
            st.session_state["rank_decrease_filter"] = False
            st.session_state["old_update_filter"] = False
    with fc4:
        if st.button("古い更新日"):
            st.session_state["old_update_filter"] = not st.session_state["old_update_filter"]
            st.session_state["sales_decrease_filter"] = False
            st.session_state["rank_decrease_filter"] = False
            st.session_state["rank_10_30_filter"] = False

    # ---- ボタン(トラフィック/売上/順位) ----
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        traffic_btn = st.button("トラフィック")
    with c2:
        sales_btn   = st.button("売上")
    with c3:
        rank_btn    = st.button("順位")

    df = load_data()
    if df.empty:
        st.warning("CSVが空、またはまだデータがありません。")
        return

    # ▼▼▼ CSSを追加して、ヘッダを改行せずスクロールする ▼▼▼
    st.markdown(
        """
        <!-- sorttable.js (クリックでソート) -->
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
            /* ヘッダは改行せずスクロール */
        }
        table.ahrefs-table thead th .header-content {
            display: inline-block;
            max-width: 120px;
            white-space: nowrap;   /* 折り返ししない */
            overflow-x: auto;      /* 横スクロール */
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
            vertical-align: middle;
            /* ここは改行可のまま (変更なし) */
            white-space: normal;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        table.ahrefs-table tbody tr:hover {
            background-color: #fafafa;
        }
        /* ソートカーソル */
        table.sortable thead {
            cursor: pointer;
        }
        table.ahrefs-table td .cell-content {
            display: inline-block;
            max-width: 400px;
            word-wrap: break-word;
        }
        /* +/− 色分け */
        .pos-change { color: green; }
        .neg-change { color: red; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # リネームマップ
    rename_map = {
        "SEO対策KW": "トップキーワード",
        "7日間平均順位": "順位",
        "30日間平均順位": "順位（30日）",
        "session": "トラフィック",
        "session_30d": "トラフィック（30日間）",
        "traffic_change_7d_vs_30d": "変更(トラフィック)",
        "sales_7d": "売上",
        "sales_30d": "売上（30日間）",
        "sales_change_7d_vs_30d": "変更(売上)",
        "post_title": "seo_title",
        "比較（7日間が良ければ＋）": "比較",
        "modified": "最終更新日"
    }

    for oldcol, newcol in rename_map.items():
        if oldcol in df.columns:
            df.rename(columns={oldcol: newcol}, inplace=True)

    # URL + seo_title
    if "URL" in df.columns and "seo_title" in df.columns:
        def combine_title_url(row):
            title_esc = html.escape(str(row["seo_title"]))
            url_esc = html.escape(str(row["URL"]))
            return (
                f'<div class="cell-content">'
                f'{title_esc}<br/>'
                f'<a href="{url_esc}" target="_blank">{url_esc}</a>'
                f'</div>'
            )
        df["URL"] = df.apply(combine_title_url, axis=1)
        df.drop(columns=["seo_title"], inplace=True)

    final_cols = [
        "URL",
        "トラフィック",
        "トラフィック（30日間）",
        "変更(トラフィック)",
        "売上",
        "売上（30日間）",
        "変更(売上)",
        "トップキーワード",
        "順位",
        "順位（30日）",
        "比較",
        "最終更新日"
    ]
    exist_cols = [c for c in final_cols if c in df.columns]
    df = df[exist_cols]

    # ▼▼▼ まずは既存のソートボタン制御 (変更なし) ▼▼▼
    if traffic_btn:
        st.session_state["traffic_sort_state"] = (st.session_state["traffic_sort_state"] + 1) % 3
        st.session_state["sales_sort_state"] = 0
        st.session_state["rank_sort_state"]  = 0
    if sales_btn:
        st.session_state["sales_sort_state"] = (st.session_state["sales_sort_state"] + 1) % 3
        st.session_state["traffic_sort_state"] = 0
        st.session_state["rank_sort_state"]    = 0
    if rank_btn:
        st.session_state["rank_sort_state"] = (st.session_state["rank_sort_state"] + 1) % 3
        st.session_state["traffic_sort_state"] = 0
        st.session_state["sales_sort_state"]   = 0

    if st.session_state["traffic_sort_state"] == 1:
        if "トラフィック" in df.columns:
            df.sort_values(by="トラフィック", ascending=False, inplace=True)
    elif st.session_state["traffic_sort_state"] == 2:
        if "トラフィック" in df.columns:
            df.sort_values(by="トラフィック", ascending=True, inplace=True)
    elif st.session_state["sales_sort_state"] == 1:
        if "売上" in df.columns:
            df.sort_values(by="売上", ascending=False, inplace=True)
    elif st.session_state["sales_sort_state"] == 2:
        if "売上" in df.columns:
            df.sort_values(by="売上", ascending=True, inplace=True)
    elif st.session_state["rank_sort_state"] == 1:
        if "順位" in df.columns:
            df.sort_values(by="順位", ascending=False, inplace=True)
    elif st.session_state["rank_sort_state"] == 2:
        if "順位" in df.columns:
            df.sort_values(by="順位", ascending=True, inplace=True)

    # ▼▼▼ フィルタ適用ロジック ▼▼▼
    # 1. 売上減少
    if st.session_state["sales_decrease_filter"]:
        # 数値をパースして -20 以下のみ抽出し、より減少率が大きい順(昇順)に
        def parse_numeric(value):
            s_clean = re.sub(r"[¥,% ]", "", str(value))
            try:
                return float(s_clean)
            except:
                return 0.0

        if "変更(売上)" in df.columns:
            df_filtered = df.copy()
            df_filtered["val"] = df_filtered["変更(売上)"].apply(parse_numeric)
            df_filtered = df_filtered[df_filtered["val"] <= -20].sort_values("val", ascending=True)
            df = df_filtered.drop(columns=["val"])

    # 2. 順位減少
    if st.session_state["rank_decrease_filter"]:
        def parse_numeric(value):
            s_clean = re.sub(r"[¥,% ]", "", str(value))
            try:
                return float(s_clean)
            except:
                return 0.0

        if "比較" in df.columns:
            df_filtered = df.copy()
            df_filtered["val"] = df_filtered["比較"].apply(parse_numeric)
            # 順位が5以上下がった = 比較(順位)が +5 以上
            df_filtered = df_filtered[df_filtered["val"] >= 5].sort_values("val", ascending=False)
            df = df_filtered.drop(columns=["val"])

    # 3. 順位10-30＋
    if st.session_state["rank_10_30_filter"]:
        def parse_numeric(value):
            s_clean = re.sub(r"[^0-9.-]", "", str(value))
            try:
                return float(s_clean)
            except:
                return 999999

        if "順位" in df.columns:
            df_filtered = df.copy()
            df_filtered["val"] = df_filtered["順位"].apply(parse_numeric)
            df_filtered = df_filtered[(df_filtered["val"] >= 10) & (df_filtered["val"] <= 30)]
            # ソートはご自由に(例:順位昇順)
            df_filtered = df_filtered.sort_values("val", ascending=True)
            df = df_filtered.drop(columns=["val"])

    # 4. 古い更新日 (6ヶ月以上前)
    if st.session_state["old_update_filter"]:
        if "最終更新日" in df.columns:
            df_filtered = df.copy()

            # 日付型に変換
            def parse_date(d):
                try:
                    return pd.to_datetime(d)
                except:
                    return pd.NaT

            df_filtered["date_val"] = df_filtered["最終更新日"].apply(parse_date)
            cutoff = pd.Timestamp.now() - pd.DateOffset(months=6)
            df_filtered = df_filtered[df_filtered["date_val"] <= cutoff]
            # 古い順にソート
            df_filtered.sort_values("date_val", ascending=True, inplace=True)
            df = df_filtered.drop(columns=["date_val"])

    # 色付け + HTML化 (既存処理そのまま)
    def color_plusminus(val, with_yen=False):
        s = str(val).strip()
        s_clean = re.sub(r"[¥, ]", "", s)
        try:
            x = float(s_clean)
        except:
            return f'<div class="cell-content">{html.escape(s)}</div>'

        if x > 0:
            sign_str = f'+{x}'
        elif x < 0:
            sign_str = str(x)
        else:
            sign_str = '0'

        if with_yen:
            if x > 0:
                sign_str = f'¥+{abs(x)}'
            elif x < 0:
                sign_str = f'¥{x}'
            else:
                sign_str = '¥0'

        if x > 0:
            return f'<div class="cell-content pos-change">{sign_str}</div>'
        elif x < 0:
            return f'<div class="cell-content neg-change">{sign_str}</div>'
        else:
            return f'<div class="cell-content">{sign_str}</div>'

    if "変更(トラフィック)" in df.columns:
        df["変更(トラフィック)"] = df["変更(トラフィック)"].apply(lambda v: color_plusminus(v, with_yen=False))
    if "変更(売上)" in df.columns:
        df["変更(売上)"] = df["変更(売上)"].apply(lambda v: color_plusminus(v, with_yen=True))
    if "比較" in df.columns:
        df["比較"] = df["比較"].apply(lambda v: color_plusminus(v, with_yen=False))

    def wrap_cell(v):
        return f'<div class="cell-content">{html.escape(str(v))}</div>'

    skip_cols = {"URL","変更(トラフィック)","変更(売上)","比較"}
    for c in df.columns:
        if c not in skip_cols:
            df[c] = df[c].apply(wrap_cell)

    new_headers = []
    for c in df.columns:
        c_strip = c.replace('<div class="cell-content">','').replace('</div>','')
        new_headers.append(f'<div class="header-content">{html.escape(c_strip)}</div>')
    df.columns = new_headers

    html_table = df.to_html(index=False, escape=False, classes=["ahrefs-table","sortable"])
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

def load_data() -> pd.DataFrame:
    try:
        return pd.read_csv("sheet_query_data.csv", encoding="utf-8-sig")
    except:
        return pd.DataFrame()

def streamlit_main():
    tab1, tab2 = st.tabs(["📊 Data Viewer", "📖 README"])
    with tab1:
        show_sheet1()
    with tab2:
        show_sheet2()

if __name__ == "__main__":
    streamlit_main()
