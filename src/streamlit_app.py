import re
import streamlit as st
import pandas as pd
import numpy as np
import html
from data_fetcher import main_fetch_all

st.set_page_config(layout="wide")

# ▼▼▼ ソート状態管理 (変更なし) ▼▼▼
if "traffic_sort_state" not in st.session_state:
    st.session_state["traffic_sort_state"] = 0
if "sales_sort_state" not in st.session_state:
    st.session_state["sales_sort_state"] = 0
if "rank_sort_state" not in st.session_state:
    st.session_state["rank_sort_state"] = 0

# ▼▼▼ 追加: フィルタ状態管理（旧コードチェックボックス） ▼▼▼
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

    # ▼ 短めの説明 (メモ表示) [旧コードのまま]
    st.info("""
    **フィルタボタンの定義**  
    - **売上減少:** 変更(売上)が -20% 以下  
    - **順位減少:** 比較(順位)が -5 以下  
    - **順位10-30＋:** 最新順位が 10〜30 の記事を抽出  
    - **古い更新日:** 最終更新日が 6ヶ月以上前
    """)

    # ▼▼▼ 旧コードのチェックボックス配置 ▼▼▼
    fc1, fc2, fc3, fc4 = st.columns(4)

    with fc1:
        st.session_state["sales_decrease_filter"] = st.checkbox(
            "売上減少", value=st.session_state["sales_decrease_filter"]
        )
    with fc2:
        st.session_state["rank_decrease_filter"] = st.checkbox(
            "順位減少", value=st.session_state["rank_decrease_filter"]
        )
    with fc3:
        st.session_state["rank_10_30_filter"] = st.checkbox(
            "順位10-30＋", value=st.session_state["rank_10_30_filter"]
        )
    with fc4:
        st.session_state["old_update_filter"] = st.checkbox(
            "古い更新日", value=st.session_state["old_update_filter"]
        )

    # ▼▼▼ 追加機能: 自動フィルタ (初期値0) ▼▼▼
    st.write("---")
    st.info("""
    **自動フィルタ(追加機能)**  
    - **売上変化閾値(円)** を入力すると、列「変更(売上)」が  
      　・閾値が **正** ⇒ その値「以上」の行を抽出  
      　・閾値が **負** ⇒ その値「以下」の行を抽出  
      (非数値は除外)  
    - **順位減少閾値** を入力すると、列「比較(順位)」がその値以下のものを抽出  
      (非数値は除外)  

    ※ 初期値は 0 なので、未入力(=0) の場合はフィルタがかからず **すべて表示** されます。
    """)
    sales_threshold = st.number_input(
        "売上変化閾値(円) (追加機能)",
        value=0.0,  # 初期値0
        step=100.0
    )
    rank_threshold = st.number_input(
        "順位減少閾値 (追加機能)",
        min_value=-100.0,
        max_value=100.0,
        value=0.0,  # 初期値0
        step=1.0
    )
    st.write("---")

    # ---- ボタン(トラフィック/売上/順位) [旧コードのまま] ----
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        traffic_btn = st.button("トラフィック")
    with c2:
        sales_btn   = st.button("売上")
    with c3:
        rank_btn    = st.button("順位")

    # ---- データ読み込み ----
    df = load_data()
    if df.empty:
        st.warning("CSVが空、またはまだデータがありません。")
        return

    # ▼▼▼ CSS (旧コードのまま) ▼▼▼
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
        }
        table.ahrefs-table thead th .header-content {
            display: inline-block;
            max-width: 120px;
            white-space: nowrap;
            overflow-x: auto;
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
            white-space: normal;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        table.ahrefs-table tbody tr:hover {
            background-color: #fafafa;
        }
        table.sortable thead {
            cursor: pointer;
        }
        table.ahrefs-table td .cell-content {
            display: inline-block;
            max-width: 400px;
            word-wrap: break-word;
        }
        .pos-change { color: green; }
        .neg-change { color: red; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ▼▼▼ リネーム [旧コードのまま] ▼▼▼
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

    # ▼▼▼ URL + seo_title 結合 [旧コードのまま] ▼▼▼
    if "URL" in df.columns and "seo_title" in df.columns:
        def combine_title_url(row):
            title_esc = html.escape(str(row["seo_title"]))
            url_esc   = html.escape(str(row["URL"]))
            return (
                f'<div class="cell-content">'
                f'{title_esc}<br/>'
                f'<a href="{url_esc}" target="_blank">{url_esc}</a>'
                f'</div>'
            )
        df["URL"] = df.apply(combine_title_url, axis=1)
        df.drop(columns=["seo_title"], inplace=True)

    # ▼▼▼ 表示列制御 [旧コードのまま] ▼▼▼
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

    # ▼▼▼ ソートボタン制御 [旧コードのまま] ▼▼▼
    if traffic_btn:
        st.session_state["traffic_sort_state"] = (st.session_state["traffic_sort_state"] + 1) % 3
        st.session_state["sales_sort_state"]   = 0
        st.session_state["rank_sort_state"]    = 0
    if sales_btn:
        st.session_state["sales_sort_state"]   = (st.session_state["sales_sort_state"] + 1) % 3
        st.session_state["traffic_sort_state"] = 0
        st.session_state["rank_sort_state"]    = 0
    if rank_btn:
        st.session_state["rank_sort_state"]    = (st.session_state["rank_sort_state"] + 1) % 3
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

    # ▼▼▼ (A) 旧コードのチェックボックス フィルタロジック ▼▼▼

    # 1. 売上減少
    if st.session_state["sales_decrease_filter"]:
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
            # 「順位が5以上下がった」 => 比較(順位) <= -5
            df_filtered = df_filtered[df_filtered["val"] <= -5].sort_values("val", ascending=True)
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
            # 10 <= 順位 <= 30
            df_filtered = df_filtered[(df_filtered["val"] >= 10) & (df_filtered["val"] <= 30)]
            df_filtered = df_filtered.sort_values("val", ascending=True)
            df = df_filtered.drop(columns=["val"])

    # 4. 古い更新日
    if st.session_state["old_update_filter"]:
        if "最終更新日" in df.columns:
            df_filtered = df.copy()
            def parse_date(d):
                try:
                    return pd.to_datetime(d)
                except:
                    return pd.NaT

            df_filtered["date_val"] = df_filtered["最終更新日"].apply(parse_date)
            cutoff = pd.Timestamp.now() - pd.DateOffset(months=6)
            df_filtered = df_filtered[df_filtered["date_val"] <= cutoff]
            df_filtered.sort_values("date_val", ascending=True, inplace=True)
            df = df_filtered.drop(columns=["date_val"])

    # ▼▼▼ (B) 新たに追加された自動フィルタ（売上変化閾値/順位減少閾値） ▼▼▼

    # 売上変化閾値が 0 以外ならフィルタを適用
    if "変更(売上)" in df.columns and sales_threshold != 0:
        def parse_sales_numeric(value):
            s_clean = re.sub(r"[¥,%\s]", "", str(value))
            try:
                return float(s_clean)
            except:
                return None  # 非数値→None

        df["__sales_val"] = df["変更(売上)"].apply(parse_sales_numeric)
        # 非数値は除外
        df = df[df["__sales_val"].notna()]

        # threshold > 0 ⇒ その値以上を表示
        # threshold < 0 ⇒ その値以下を表示
        if sales_threshold > 0:
            df = df[df["__sales_val"] >= sales_threshold]
        else:  # sales_threshold < 0
            df = df[df["__sales_val"] <= sales_threshold]

        df.drop(columns=["__sales_val"], inplace=True)

    # 順位減少閾値が 0 以外ならフィルタを適用
    if "比較" in df.columns and rank_threshold != 0:
        def parse_rank_numeric(value):
            s_clean = re.sub(r"[^0-9.-]", "", str(value))
            try:
                return float(s_clean)
            except:
                return None
        df["__rank_val"] = df["比較"].apply(parse_rank_numeric)
        # 非数値は除外
        df = df[df["__rank_val"].notna()]
        # 入力された閾値以下のみ表示 (Rank は基本 “減少” に対する指標なので従来どおり <=)
        df = df[df["__rank_val"] <= rank_threshold]
        df.drop(columns=["__rank_val"], inplace=True)

    # ▼▼▼ 色付け + HTML化 (旧コードそのまま) ▼▼▼
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

    skip_cols = {"URL", "変更(トラフィック)", "変更(売上)", "比較"}
    for c in df.columns:
        if c not in skip_cols:
            df[c] = df[c].apply(wrap_cell)

    new_headers = []
    for c in df.columns:
        c_strip = c.replace('<div class="cell-content">','').replace('</div>','')
        new_headers.append(f'<div class="header-content">{html.escape(c_strip)}</div>')
    df.columns = new_headers

    # HTMLテーブル化
    html_table = df.to_html(index=False, escape=False, classes=["ahrefs-table","sortable"])
    st.write(html_table, unsafe_allow_html=True)


###################################
# (Hidden) README doc (旧コードのまま)
###################################

README_TEXT = """\

## Rewrite Priority Score（リライト優先度）について

成果を伸ばしやすい記事を優先的にリライトするために、売上・CV・アクセス数・検索順位などの指標を統合したスコアです。売上が高い記事はもちろん、検索順位が上昇傾向にある記事も見逃さないようバランス良く評価します。

---

## 算出の概要

Rewrite Priority Score = （売上、CV、PV、検索順位など） をログ変換や重み付けで合算し、高順位・高CV・伸びしろがある記事を優先表示します。

> **ポイント**
> - 売上がある記事の伸ばし効果を重視
> - 順位が最近上昇している記事を捉える
> - シンプルかつ汎用的な指標にまとめる

これにより、効率的にリライトが行え、ビジネス成果に直結しやすい記事から着手できます。
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
