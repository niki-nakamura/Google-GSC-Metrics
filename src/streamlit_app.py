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

## この表の目的

- **目的**  
  - 「どの記事からリライトに取り組むべきか？」を即座に判断するためのテーブルです。
  - **Rewrite Priority Score**（リライト優先度）を算出し、降順ソートすることで、成果改善の見込みがある記事から効率的にリライトを進めることができます。
  - 直近7日間の指標（アクセスや売上、CVなど）を中心に、検索順位の改善度合いもあわせて可視化しています。

## 集計対象

- WordPress 投稿のうち `ONTENT_TYPE` が「column」の記事をメインとします。
- 直近7日間のセッション数やPV数、コンバージョン（CV）などの数値は BigQuery から取得。
- シート上の情報（カテゴリ・SEO対策KW など）は WordPress DB を元に紐づけ。

---

## 全項目一覧と説明

| カラム名                       | 説明・役割                                                                                                                                                                                                                   |
|--------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **CONTENT_TYPE**               | 記事の投稿タイプ（例: “column”など）。一覧作成時のフィルタに利用。                                                                                                                                                           |
| **POST_ID**                    | WordPress の投稿ID。一意に記事を識別。                                                                                                                                                                                       |
| **URL**                        | 記事URL。クリックすると該当記事へアクセス可能。                                                                                                                                                                             |
| **category**                   | カテゴリー名の一覧。複数ある場合はカンマ区切り。                                                                                                                                                                              |
| **post_title**                 | 記事タイトル。                                                                                                                                                                                                               |
| **session**                    | 直近7日間のセッション数（平均）。ユーザーが記事を訪問した回数の指標。                                                                                                                                                        |
| **page_view**                  | 直近7日間のページビュー数（平均）。記事がどの程度閲覧されたかを示す。                                                                                                                                                        |
| **click_app_store**            | App Store などアプリストアへのクリック数（7日平均）。アプリ紹介記事などでストアへ誘導した回数。                                                                                                                                |
| **article_ctr**                | 記事内クリック率（7日平均）。記事内リンクのクリック総数を表示回数で割ったCTRなどから算出。                                                                                                                                   |
| **imp**                        | 検索インプレッション（7日平均）。検索結果に表示された推定回数。                                                                                                                                                              |
| **click**                      | 検索クリック数（7日平均）。検索結果を実際にクリックされた回数。                                                                                                                                                              |
| **search_ctr**                 | 検索CTR（7日平均）。 `click / imp` で算出された検索クリック率。                                                                                                                                                             |
| **sum_position**               | 検索順位の合計など一時的な集計値。アプリ表示時には非表示にすることが多い。                                                                                                                                                   |
| **avg_position**               | 検索平均順位（7日平均）。値が小さいほど上位。                                                                                                                                                                                 |
| **sales**                      | 過去7日間の平均売上金額（アフィリエイト収益など）。                                                                                                                                                                           |
| **pv_unit_sales**              | PVあたりの売上貢献度を概算したもの。`sales / page_view` などで1PV当たりの売上を把握。                                                                                                                                       |
| **app_link_click**             | アプリ紹介リンクなどのクリック数（7日平均）。                                                                                                                                                                                  |
| **cv**                         | コンバージョン数（7日平均）。問い合わせ、会員登録など、サイトが狙う成果指標。                                                                                                                                                 |
| **cvr**                        | CVR（コンバージョン率）。`cv / session` などで算出。                                                                                                                                                                         |
| **growth_rate**                | 過去30日間平均順位 → 7日間平均順位 にかけての **順位改善率(%)**。<br>計算式：<br>\[ \frac{(\text{30日間平均順位} - \text{7日間平均順位})}{\text{30日間平均順位}} \times 100 \]<br>プラスの値が大きいほど、最近順位が上がっている（改善している）ことを示す。 |
| **SEO対策KW**                 | その記事が狙う主なSEOキーワード。                                                                                                                                                                                             |
| **30日間平均順位**             | 過去30日間の検索順位平均。                                                                                                                                                                                                    |
| **7日間平均順位**              | 過去7日間の検索順位平均。                                                                                                                                                                                                     |
| **比較（7日間が良ければ＋）**  | 「7日間平均順位 - 30日間平均順位」。プラスの場合は順位が改善している傾向。                                                                                                                                                   |

> ※ 上記の数値はいずれも「直近7日 or 30日」での平均値。PV数や売上の絶対値には誤差や推定を含む場合あり。

---

## Rewrite Priority Score（リライト優先度）

### 1. 何のための指標か

- **売上やCVが見込める記事を効率的にリライトし、検索順位や収益をさらに伸ばすため**の独自スコアです。  
- 「直近で売上実績がある」「PV/インプレッションが多い」「順位が改善傾向にある」「さらに伸びしろがある」といった要素をまとめて数値化し、優先度の高い記事を上位に抽出します。

### 2. スコアの算出方法

例えば以下のように重み付け & 対数変換を行い、合算して1つのスコアにしています。

\[
\text{Rewrite Priority Score} = 
  \Bigl(\log(\text{sales}+1) \times w_{\mathrm{sales}}\Bigr)
  + \Bigl(\text{cv} \times w_{\mathrm{cv}}\Bigr)
  + \Bigl(\log(\text{page\_view}+1) \times w_{\mathrm{pv}}\Bigr)
  + \Bigl(\log(\text{imp}+1) \times w_{\mathrm{imp}}\Bigr)
  + \Bigl(\text{growth\_rate} \times w_{\mathrm{gr}}\Bigr)
  - \Bigl(\text{avg\_position} \times w_{\mathrm{pos}}\Bigr)
\]

- **対数変換**: `log(X + 1)`  
  - 「sales」「page_view」「imp」など数値が大きく振れる指標をログ圧縮し、極端な差を平準化。  
- **重み付け**:  
  - 例: `w_sales = 1.0`, `w_cv = 1.0`, `w_pv = 0.5` など  
  - 売上やCVを重視しつつ、PVやインプレッションも程よく加点する一方で、平均順位はマイナス評価 (順位が高い=数値が小さいほど加点が大きい) として組み込む。
- **最終ソート**  
  - ボタン押下時に「sales=0 の記事を除外」→ スコア計算→ 降順ソート。スコアが高い順にリライト候補を上位表示。

### 3. どう有意義か

- **成果向上に直結する記事を選別**  
  - 既に売上やCVがある & PV/impが多い & 順位改善傾向の記事を上位に抽出→ リライト効果が出やすい。  
- **定量データに基づく意思決定**  
  - リライト対象を経験や勘に頼らず、売上/PV/順位といった客観データで優先度を決められる。  
- **事業効率の向上**  
  - 優先度が高い記事から着手することで、限られたリソースで最大限の成果を狙える。

### 4. 使用方法

1. **Rewrite Priority Score でソート**  
   - 「Rewrite Priority Scoreで降順ソート」ボタンを押すと、売上>0の記事のみを対象にスコアを計算し、上位から並べ替えます。
2. **上位記事からリライト**  
   - 収益・検索効果の改善が見込める優先度の高い記事を優先的に強化することで、リライト施策の効率が上がります。

---

## このテーブルを使った具体的な流れ

1. **記事データの現状把握**  
   - カテゴリやタイトル、PV、売上、順位などを比較し、どの記事がどのくらい成果を出しているか一目で確認。
2. **リライト対象の抽出**  
   - Rewrite Priority Score を使って、収益向上が期待できる記事から着手する。
3. **順位変動の確認**  
   - 「比較（7日間が良ければ＋）」や `growth_rate` で、最近順位が上がっているのか下がっているのかを判断。さらに伸びそうな記事を重点的に強化するなどの戦略立案に活用。
4. **リライト後の効果測定**  
   - 翌週以降のデータを再度取り込み、スコアの変化や売上・順位などがどう変わったかを追跡し、PDCAを回す。

---

### データ取得範囲（BigQuery）

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
