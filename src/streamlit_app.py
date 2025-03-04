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

        # (2) 数値化処理
        for cname in ["sales","cv","page_view","imp","growth_rate","avg_position"]:
            if cname in df.columns:
                df[cname] = pd.to_numeric(df[cname], errors="coerce").fillna(0)

        # (3) 重み付け
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

            score = (np.log(s+1) * w_sales
                     + c           * w_cv
                     + np.log(pv+1)* w_pv
                     + np.log(imp+1)* w_imp
                     + gr          * w_gr
                     - pos         * w_pos)
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

## この表の目的

- **目的**  
  - 「どの記事からリライトに取り組むべきか？」を即座に判断するためのテーブルです。
  - **Rewrite Priority Score**（リライト優先度）を算出し、降順ソートすることで、成果改善の見込みがある記事から効率的にリライトを進めることができます。
  - 直近7日間の指標（アクセスや売上、CVなど）を中心に、検索順位の改善度もあわせて可視化しています。

## 集計対象

- WordPress 投稿のうち `ONTENT_TYPE` が「column」の記事が主な対象です。
- 直近7日間のセッションやPV、コンバージョン等の数値データは BigQuery から取得しています。
- シート上の他の情報（カテゴリ・SEO対策KW など）は WordPress DB から紐づけしています。

## 全項目一覧と説明

| カラム名                         | 説明・役割                                                                                                                      |
|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| **ONTENT_TYPE**                 | 記事の投稿タイプ（例: “column” など）。リスト化の際にフィルタに使用。                                                           |
| **POST_ID**                     | WordPress の投稿 ID。記事を一意に識別するための番号。                                                                            |
| **URL**                         | 記事の URL。クリックすると該当記事へアクセス可能。                                                                              |
| **category**                    | 記事のカテゴリー名（複数の場合はカンマ区切り）。                                                                                |
| **post_title**                  | 記事のタイトル。                                                                                                              |
| **session**                     | 過去7日間の「セッション数」平均値。ユーザーが記事を訪問した回数の指標。                                                        |
| **page_view**                   | 過去7日間の「ページビュー数」平均値。閲覧ページ数の合計を示す指標。                                                             |
| **click_app_store**             | App Store 等へのクリック回数（7日間平均）。アプリ紹介記事などでアプリストアへ誘導した数。                                        |
| **article_ctr**                 | 過去7日間の「記事内クリック率」。クリック数 / 表示回数などから導出される記事内 CTR。                                             |
| **imp**                         | 検索インプレッション（7日間平均）。検索結果に表示された回数の推定値。                                                           |
| **click**                       | 検索クリック数（7日間平均）。検索結果から実際にクリックされた回数。                                                             |
| **search_ctr**                  | 検索 CTR（7日間平均）。click / imp から算出されるクリック率。                                                                  |
| **sum_position**                | 検索順位合計などの一時的集計値。表示時には非表示にする場合あり。                                                                |
| **avg_position**                | 検索平均順位（7日間）。検索で何位に表示されるかの平均値。                                                                       |
| **sales**                       | 過去7日間の平均売上金額（アフィリエイトや広告収益など）。                                                                       |
| **pv_unit_sales**               | 「PVあたりの売上」を概算したもの。page_view / sales 等の計算で導き、1PVあたりの売上貢献度を見る指標。                          |
| **app_link_click**              | アプリリンクのクリック数（7日間平均）。アプリ紹介記事などでリンクをタップした回数。                                              |
| **cv**                          | 7日間平均のコンバージョン数。問い合わせや会員登録など、サイトが狙う成果指標。                                                   |
| **cvr**                         | CVR（コンバージョン率）。cv / session などで算出する、ユーザー訪問のうちコンバージョンした割合。                                 |
| **growth_rate**                 | 過去30日間平均順位 → 7日間平均順位 にかけての **順位改善率(%)**。<br><br>
計算式：<br>
\[
\frac{(\text{30日間平均順位} - \text{7日間平均順位})}{\text{30日間平均順位}} \times 100
\]<br>
プラスの値が大きいほど、最近順位が上がっている（改善している）ことを示します。 |
| **SEO対策KW**                   | その記事が狙う主となる SEO キーワード。                                                   |
| **30日間平均順位**             | 過去30日間の検索順位平均。                                                               |
| **7日間平均順位**               | 過去7日間の検索順位平均。                                                                |
| **比較（7日間が良ければ＋）**   | 「7日間平均順位 - 30日間平均順位」。<br>プラスの場合は順位が改善している傾向。           |

> ※ これらの数値はすべて過去7日や30日を平均化したもので、記事の PV 数や売上等の絶対値には多少の誤差や推定を含みます。

---

## Rewrite Priority Score（リライト優先度）

### 1. 何のための指標か

- 売上やCVが見込める記事を効率的にリライトし、検索順位や収益をさらに伸ばすための独自スコアです。  
- 「直近で売上実績がある」「PV・impが大きい」「順位が改善傾向」「さらに伸びしろがある」という要素を総合的に数値化して、優先度を算出しています。

### 2. スコアの算出方法

以下のような式で重み付け＆対数変換を行い、トータルスコアに合算します。

\[
  \text{Rewrite Priority Score} = 
  \Bigl(\log(\text{sales}+1) \times w_{\mathrm{sales}}\Bigr)
  + \Bigl(\text{cv} \times w_{\mathrm{cv}}\Bigr)
  + \Bigl(\log(\text{page\_view}+1) \times w_{\mathrm{pv}}\Bigr)
  + \Bigl(\log(\text{imp}+1) \times w_{\mathrm{imp}}\Bigr)
  + \Bigl(\text{growth\_rate} \times w_{\mathrm{gr}}\Bigr)
  - \Bigl(\text{avg\_position} \times w_{\mathrm{pos}}\Bigr)
\]

- **対数変換**: `np.log(X+1)`  
  - 「sales」や「page_view」「imp」など桁が大きくなりがちな指標をログ圧縮し、極端な値の影響を緩和。
- **重み付け**  
  - 例として  
    - \( w_{\mathrm{sales}} = 1.0\)  
    - \( w_{\mathrm{cv}} = 1.0\)  
    - \( w_{\mathrm{pv}} = 0.5\)  
    - \( w_{\mathrm{imp}} = 0.5\)  
    - \( w_{\mathrm{gr}} = 0.3\)  
    - \( w_{\mathrm{pos}} = 0.2\)  
  - 各指標にどれだけ重みを置くか調整。たとえば「売上(sales)」と「CV」は1.0で重視し、「PVやimp」は0.5など控えめにしつつも考慮し、「順位が高い(数値が小さい)ほどプラス評価」とするために avg_position はマイナス要素として計算に組み込む。

### 3. どう有意義か

- **伸ばしやすい記事を一目で把握できる**  
  - 収益やコンバージョン、流入量(PV/imp)がすでに一定あり、さらに検索順位が改善傾向にある記事ほどスコアが上がるため、**「少し手を入れるだけで伸びやすい記事」**の発見に役立ちます。
- **事業効率が高まる**  
  - このスコアが高い記事から優先的にリライトを行うことで、リライト施策による収益アップ・順位改善を効果的に狙えます。
- **数値根拠に基づいた意思決定**  
  - 個人的な感覚だけでなく、売上やPV、順位改善度を踏まえた定量的根拠をもってリライト対象を決められます。

### 4. 使用方法

1. **Rewrite Priority Score でソート**  
   - 「Rewrite Priority Score で降順ソート」のボタンを押すと、**sales = 0** の記事を除外したうえでスコアを計算し、上位から並べ替えます。  
2. **リスト上位からリライト**  
   - スコアが高い記事＝ビジネス成果につながりやすい記事から着手すると効率的です。

---

## この表（および CSV）の活用方法

1. **現状把握**  
   - どのカテゴリー（category）やタイトル（post_title）が、どの程度の売上・アクセスを稼いでいるか一目でわかります。
2. **リライト優先度の判断**  
   - リライト対象を「Rewrite Priority Score」の高い順に抽出すると、伸ばしやすい記事から改善できるため事業効率が高まります。
3. **検索順位の変動確認**  
   - 「比較（7日間が良ければ＋）」や「growth_rate」によって、順位が上がっているか下がっているかを俯瞰でき、将来さらに強化すべき記事を把握できます。
4. **成果確認・改善サイクル**  
   - リライト後、翌週以降の再集計で数値変化を追跡し、PDCAを回すことで継続的な改善が見込めます。

---

### データ取得範囲 (BigQuery)

```sql
DECLARE DS_START_DATE STRING DEFAULT FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY));
DECLARE DS_END_DATE   STRING DEFAULT FORMAT_DATE('%Y%m%d', CURRENT_DATE());


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
