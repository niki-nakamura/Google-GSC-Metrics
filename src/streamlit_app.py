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
以下は、README のリライト例です。Rewrite Priority Score（リライト優先度）の計算方法や、なぜ「Rewrite Priority Score での降順ソート順」に従ってリライトすべきかをわかりやすくまとめています。

---

## この表の目的

- **どの記事を優先してリライトすべきか** を即座に判断するためのダッシュボードです。
- 直近7日間のアクセス数や売上、検索順位などを総合し、**Rewrite Priority Score**（リライト優先度）を算出。
- 売上やCV(コンバージョン)の伸びしろが大きく、さらに検索順位が上がり始めている記事を抽出して、効率よくリライトを行うための指標を提供します。

---

## 集計対象

- WordPress投稿のうち、`ONTENT_TYPE` が「column」の記事を中心に対象としています。
- BigQuery から直近7日・30日単位のデータを取得（PV・セッション数・売上など）。
- WordPress DB からカテゴリ、SEOキーワードなどを紐づけて一覧化しています。

---

## 全項目一覧と説明

| カラム名                       | 説明                                                                                                                                                                                                                      |
|--------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **CONTENT_TYPE**               | 記事投稿タイプ（例：「column」など）。記事一覧作成時のフィルタで使用。                                                                                                                                                   |
| **POST_ID**                    | WordPress の投稿ID。一意に記事を識別。                                                                                                                                                                                    |
| **URL**                        | 記事URL。クリックで実際の記事を開ける。                                                                                                                                                                                  |
| **category**                   | カテゴリー名（複数の場合はカンマ区切り）。                                                                                                                                                                               |
| **post_title**                 | 記事タイトル。                                                                                                                                                                                                            |
| **session**                    | 直近7日間のセッション数。ユーザーが記事を訪問した回数。                                                                                                                                                                  |
| **page_view**                  | 直近7日間のページビュー数。記事がどの程度閲覧されたかを示す。                                                                                                                                                            |
| **click_app_store**            | App Store などへのクリック数（7日平均）。アプリ紹介記事などでの誘導回数。                                                                                                                                                  |
| **article_ctr**                | 記事内リンククリック率（7日平均）。記事内部リンクのクリック総数 ÷ 表示回数 などから算出。                                                                                                                                |
| **imp**                        | 検索インプレッション（7日平均）。検索結果として何回表示されたか。                                                                                                                                                         |
| **click**                      | 検索クリック数（7日平均）。検索結果から実際にクリックされた回数。                                                                                                                                                         |
| **search_ctr**                 | 検索CTR（7日平均）。`click / imp` で算出。                                                                                                                                                                              |
| **sum_position**               | 検索順位の合計などの一時集計列。アプリ表示では非表示に設定。                                                                                                                                                             |
| **avg_position**               | 検索平均順位（7日平均）。値が小さいほど上位。                                                                                                                                                                             |
| **sales**                      | 過去7日間の平均売上金額（アフィリエイト収益など）。                                                                                                                                                                       |
| **pv_unit_sales**              | PVあたりの売上貢献度を概算したもの。`sales / page_view` などで 1PV当たりの売上を把握。                                                                                                                                    |
| **app_link_click**             | アプリ紹介リンクなどのクリック数（7日平均）。                                                                                                                                                                             |
| **cv**                         | コンバージョン数（7日平均）。問い合わせや会員登録などサイト目標の成果指標。                                                                                                                                               |
| **cvr**                        | コンバージョン率（CVR）。`cv / session` などで算出。                                                                                                                                                                     |
| **growth_rate**                | 30日間平均順位→7日間平均順位への **順位改善率(%)**。<br>計算式：<br> \[ \((\text{30日平均順位} - \text{7日平均順位}) ÷ \text{30日平均順位}\) × 100 \]<br>プラスの値が大きいほど、最近順位が伸びている。 |
| **SEO対策KW**                 | 当該記事が狙う主なSEOキーワード。                                                                                                                                                                                         |
| **30日間平均順位**             | 過去30日間の検索平均順位。                                                                                                                                                                                                |
| **7日間平均順位**              | 過去7日間の検索平均順位。                                                                                                                                                                                                 |
| **比較（7日間が良ければ＋）**  | 「7日間平均順位 - 30日間平均順位」。プラスの場合は順位が改善している。                                                                                                                                                    |

---

## Rewrite Priority Score（リライト優先度）

### 1. スコアの役割
- **売上やCVをさらに伸ばす可能性の高い記事**を絞り込む独自指標です。  
- 売上・CV・PV・検索順位など、成果に直結する要素を総合的に評価し、**「今リライトすべき優先度」** を数値化しています。

### 2. スコアの算出方法

Rewrite Priority Score は、以下のように主な指標に対数変換を加えて合算し、**売上**や**CV**を最重視しつつ、**PV**や**インプレッション**(imp)、**順位改善率**(growth_rate)なども取り入れる形で計算します。

\[
\text{Rewrite Priority Score} 
= (\log(\text{sales}+1)\times w_{\mathrm{sales}})
+ (\text{cv}\times w_{\mathrm{cv}})
+ (\log(\text{page\_view}+1)\times w_{\mathrm{pv}})
+ (\log(\text{imp}+1)\times w_{\mathrm{imp}})
+ (\text{growth\_rate}\times w_{\mathrm{gr}})
- (\text{avg\_position}\times w_{\mathrm{pos}})
\]

- **対数変換**: `log(X + 1)`  
  極端に大きな数値（例: PVやインプレッション）がある場合の影響を抑え、よりバランスの取れた評価を行うためにログ圧縮を適用しています。
- **重み付け**:  
  たとえば `w_sales = 1.0`, `w_cv = 1.0` のように、売上やCVの影響を大きめに設定。PVやimpはやや控えめに加点し、順位（avg_position）は数値が小さいほどプラス評価になるようにマイナス要素として組み込みます（高順位ほどスコアは大きくなる）。

### 3. なぜ「Rewrite Priority Score での降順ソート」順にリライトすべきか

1. **売上が出ている記事を優先できる**  
   - ボタン押下時には「sales=0」の記事を除外して計算するため、すでに売上実績がある記事のみがソート対象になります。  
   - これにより「リライトによって実際に売上が増えやすい記事」から着手でき、投下リソースを効率よく使えます。

2. **“あと少しで伸びそう” という記事を見逃さない**  
   - PVやインプレッションが一定数あり、順位改善も始まっている記事はリライト効果が高いと想定されます。  
   - Rewrite Priority Score により「売上・CVがあり、PV/impもそこそこ多く、順位が上がってきている」記事ほど上位に表示されます。

3. **定量データに基づく合理的なリライトの優先度決定**  
   - 経験や勘だけでなく、**客観的な数値**（売上、PV、順位、伸び率）に基づいて優先度を決めるため、成果につながりやすいリライト施策を展開しやすい。

---

## このテーブルを使った具体的な活用方法

1. **一覧で現状把握**  
   - カテゴリ・タイトル・売上・PV・順位などを比較し、どの記事がどの程度成果を出しているかを素早く確認。
2. **Rewrite Priority Scoreでフィルタ＆ソート**  
   - 「Rewrite Priority Scoreで降順ソート」ボタンを押すと、売上 > 0 の記事のみが対象になり、スコアを計算して高い順に並び替えます。  
   - スコアが高い記事から順番にリライト・コンテンツ強化を行うことで、効果を最大化しやすくなります。
3. **PDCAサイクルを回す**  
   - リライト後は再度データを集計してスコアを確認し、売上や順位の変化を追跡。  
   - スコアの変動を見ながら改善施策を繰り返すことで、サイト全体の成果向上を狙います。

---

### データ取得範囲（BigQuery）の例

```sql
DECLARE DS_START_DATE STRING DEFAULT FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY));
DECLARE DS_END_DATE   STRING DEFAULT FORMAT_DATE('%Y%m%d', CURRENT_DATE());

-- この間の期間を対象にPVなどを集計
```

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
