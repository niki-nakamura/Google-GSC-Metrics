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

        /* ヘッダー部分のセルも nowrap + 横スクロール可能にする */
        table.customtable thead th .header-content {
            display: inline-block;
            max-width: 120px;      /* 列幅をある程度固定 */
            white-space: nowrap;   /* 改行を許可しない */
            overflow-x: auto;      /* はみ出す場合はスクロール */
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
