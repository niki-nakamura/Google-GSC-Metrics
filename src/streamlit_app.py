import re
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
    # ---------------------------
    # 1) ページタイトル
    # ---------------------------
    st.subheader("上位ページ")

    # ---------------------------
    # 2) CSVを読み込み
    # ---------------------------
    df_original = load_data()
    if df_original.empty:
        st.warning("CSVが空、またはまだデータがありません。")
        return

    # ---------------------------
    # 3) セッション状態の初期化
    #   - df_original: 元の並びを保管
    #   - traffic_sort_state, sales_sort_state, rank_sort_state: 0(元の表示) / 1(降順) / 2(昇順)
    # ---------------------------
    if "df_original" not in st.session_state:
        st.session_state["df_original"] = df_original.copy()

    if "traffic_sort_state" not in st.session_state:
        st.session_state["traffic_sort_state"] = 0  # 0: 元, 1: 降順, 2: 昇順
    if "sales_sort_state" not in st.session_state:
        st.session_state["sales_sort_state"] = 0
    if "rank_sort_state" not in st.session_state:
        st.session_state["rank_sort_state"] = 0

    # ---------------------------
    # 4) リネームマップ
    # ---------------------------
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
        "比較（7日間が良ければ＋）": "比較"
    }
    for oldcol, newcol in rename_map.items():
        if oldcol in df_original.columns:
            df_original.rename(columns={oldcol: newcol}, inplace=True)

    # ---------------------------
    # 5) URL列に seo_title を含める
    # ---------------------------
    if "URL" in df_original.columns and "seo_title" in df_original.columns:
        def combine_title_url(row):
            title_esc = html.escape(str(row["seo_title"]))
            url_esc = html.escape(str(row["URL"]))
            return (
                f'<div class="cell-content">'
                f'{title_esc}<br/>'
                f'<a href="{url_esc}" target="_blank">{url_esc}</a>'
                f'</div>'
            )
        df_original["URL"] = df_original.apply(combine_title_url, axis=1)
        df_original.drop(columns=["seo_title"], inplace=True)

    # ---------------------------
    # 6) 表示したい列
    # ---------------------------
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
        "比較"
    ]
    exist_cols = [c for c in final_cols if c in df_original.columns]
    df_original = df_original[exist_cols]

    # ------------------------------------------------
    # 7) ボタンの配置 (トラフィック / 売上 / 順位)
    #    各ボタンを押すと 3段階(降順→昇順→元に戻す) を切替
    # ------------------------------------------------
    colA, colB, colC = st.columns(3)

    with colA:
        traffic_btn = st.button("トラフィック")
    with colB:
        sales_btn   = st.button("売上")
    with colC:
        rank_btn    = st.button("順位")

    # ここでボタンが押されたら対応する state を +1 し、他をリセット
    # 0 → 1(降順) → 2(昇順) → 0(元) → ...
    if traffic_btn:
        st.session_state["traffic_sort_state"] = (st.session_state["traffic_sort_state"] + 1) % 3
        # 他はリセット
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

    # dfを再取得 (元の並び)
    df = st.session_state["df_original"].copy()

    # ------------------------------------------------
    # 8) ソートの適用
    #    traffic_sort_state, sales_sort_state, rank_sort_state のいずれか
    # ------------------------------------------------

    # 1) トラフィックソート
    if st.session_state["traffic_sort_state"] == 1:
        # 降順
        if "トラフィック" in df.columns:
            df.sort_values(by="トラフィック", ascending=False, inplace=True)
    elif st.session_state["traffic_sort_state"] == 2:
        # 昇順
        if "トラフィック" in df.columns:
            df.sort_values(by="トラフィック", ascending=True, inplace=True)
    # 0 => 元の状態(何もしない)

    # 2) 売上ソート
    elif st.session_state["sales_sort_state"] == 1:
        # 降順
        if "売上" in df.columns:
            # '売上' が数値でない場合は parseが要るかもしれないが
            # CSV由来なら floatにできる想定
            df.sort_values(by="売上", ascending=False, inplace=True)
    elif st.session_state["sales_sort_state"] == 2:
        # 昇順
        if "売上" in df.columns:
            df.sort_values(by="売上", ascending=True, inplace=True)

    # 3) 順位ソート (多い順→少ない順→元)
    #   順位は小さいほど上位だが、ここでは多い順(= descending) = 
    #   → ascending logic might be reversed
    elif st.session_state["rank_sort_state"] == 1:
        # 多い順 => descending
        if "順位" in df.columns:
            df.sort_values(by="順位", ascending=False, inplace=True)
    elif st.session_state["rank_sort_state"] == 2:
        # 少ない順 => ascending
        if "順位" in df.columns:
            df.sort_values(by="順位", ascending=True, inplace=True)

    # 0 => 何もしない

    # ------------------------------------------------
    # 9) 色付けロジック (変更(トラフィック), 変更(売上), 比較)
    # ------------------------------------------------
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

    # 変更(トラフィック)
    if "変更(トラフィック)" in df.columns:
        df["変更(トラフィック)"] = df["変更(トラフィック)"].apply(lambda v: color_plusminus(v, with_yen=False))
    # 変更(売上) => yen=True
    if "変更(売上)" in df.columns:
        df["変更(売上)"] = df["変更(売上)"].apply(lambda v: color_plusminus(v, with_yen=True))
    # 比較 => yen=False
    if "比較" in df.columns:
        df["比較"] = df["比較"].apply(lambda v: color_plusminus(v, with_yen=False))

    # ------------------------------------------------
    # 10) 他の列をラップ
    # ------------------------------------------------
    def wrap_cell(v):
        return f'<div class="cell-content">{html.escape(str(v))}</div>'

    skip_cols = {"URL","変更(トラフィック)","変更(売上)","比較"}
    for c in df.columns:
        if c not in skip_cols:
            df[c] = df[c].apply(wrap_cell)

    # ------------------------------------------------
    # 11) ヘッダを <div class="header-content">
    # ------------------------------------------------
    new_headers = []
    for c in df.columns:
        c_strip = c.replace('<div class="cell-content">','').replace('</div>','')
        new_headers.append(f'<div class="header-content">{html.escape(c_strip)}</div>')
    df.columns = new_headers

    # ------------------------------------------------
    # 12) HTML出力
    # ------------------------------------------------
    html_table = df.to_html(index=False, escape=False, classes=["ahrefs-table", "sortable"])
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
