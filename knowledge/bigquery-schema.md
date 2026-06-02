# BigQuery スキーマ・クエリ参考

## 接続情報

| 項目 | 値 |
|---|---|
| プロジェクトID | `bigquery-jukust` |
| リージョン | `asia-northeast1`（東京） |
| 認証方式 | OAuth token.json（**サービスアカウント禁止**） |

### 認証コード（Python）

```python
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth-oauthlib

from google.oauth2.credentials import Credentials
from google.cloud import bigquery

TOKEN_FILE = r"/Users/119322/claude-code-template_af\secrets\token.json"
SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/drive',
]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
client = bigquery.Client(project="bigquery-jukust", credentials=creds)
```

---

## CA Meta広告 主要ビュー

### `v_CA_meta_ads_daily_report_with_scenario`

CA Meta広告の日次実績とシナリオ情報を結合したビュー。**最もよく使う**。

| カラム名 | 型 | 意味 | 備考 |
|---|---|---|---|
| `date` | DATE | 日付 | |
| `ad_name` | STRING | 広告名（命名規則準拠） | |
| `adset_name` | STRING | 広告セット名 | |
| `campaign_name` | STRING | キャンペーン名 | |
| `spend` | FLOAT | 広告費（円） | |
| `impressions` | INTEGER | インプレッション数 | |
| `link_clicks` | INTEGER | リンククリック数 | |
| `purchase` | INTEGER | **LINE購入CV（最重要）** | FV登録に相当 |
| `scenario_text` | STRING | シナリオ本文 | NULLの場合あり |
| `age_range` | STRING | ターゲット年齢帯 | |
| `gender` | STRING | ターゲット性別 | |

### `v_CA_meta_ads_demographics_report_with_scenario`

年齢・性別別のデモグラフィクスビュー。CVRのセグメント分析に使う。

| カラム名 | 型 | 意味 |
|---|---|---|
| `date` | DATE | 日付 |
| `ad_name` | STRING | 広告名 |
| `age` | STRING | 年齢帯（例: `25-34`） |
| `gender` | STRING | 性別（`male`/`female`/`unknown`） |
| `impressions` | INTEGER | インプレッション数 |
| `link_clicks` | INTEGER | クリック数 |
| `purchase` | INTEGER | CV数 |
| `spend` | FLOAT | 広告費 |

---

## ST Meta広告 主要ビュー

### `ST_meta_rpt.v_ST_meta_campaign_report`

ST Meta広告の日次実績＋シナリオ結合ビュー。**STの分析はこれを使う**。

| カラム名 | 型 | 意味 | 備考 |
|---|---|---|---|
| `target_date` | DATE | 配信日付 | ※`date`ではなく`target_date` |
| `ad_name` | STRING | 広告名 | |
| `canonical_ad_name` | STRING | 正規化済み広告名 | |
| `adset_name` | STRING | 広告セット名 | |
| `campaign_name` | STRING | キャンペーン名 | |
| `spend` | FLOAT | 広告費（円） | |
| `impressions` | INTEGER | インプレッション数 | |
| `link_clicks` | INTEGER | リンククリック数 | |
| `complete_registration` | FLOAT | **LINE登録CV（最重要KPI）** | CAの`purchase`相当 |
| `custom_cv_2` | FLOAT | 応募CV候補 | |
| `video_view_3s` | INTEGER | 3秒再生数 | |
| `video_p25` | INTEGER | 動画25%再生数 | |
| `video_p50` | INTEGER | 動画50%再生数 | |
| `video_p75` | INTEGER | 動画75%再生数 | |
| `video_p100` | INTEGER | 動画100%再生数 | |
| `scenario` | STRING | シナリオ本文 | NULLの場合あり |

---

## クエリパターン

### CA：広告別90日集計（クリエイティブ評価用）

BigQueryのビューに直接 `GROUP BY + HAVING` を書くとエラーになる。**必ずCTEを使う**。

```sql
WITH agg AS (
  SELECT
    ad_name,
    SUM(spend)       AS spend,
    SUM(purchase)    AS purchase,
    SUM(link_clicks) AS link_clicks
  FROM `bigquery-jukust.CA_meta_rpt.v_CA_meta_ads_daily_report_with_scenario`
  WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
  GROUP BY ad_name
)
SELECT
  ad_name,
  spend,
  purchase,
  SAFE_DIVIDE(spend, purchase)       AS cpa,
  SAFE_DIVIDE(purchase, link_clicks) AS cvr
FROM agg
WHERE spend >= 10000   -- 1万円未満は統計的に不安定なため除外
ORDER BY cpa ASC
```

### ST：広告別90日集計（クリエイティブ評価用）

```sql
WITH agg AS (
  SELECT
    ad_name,
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS cv,
    SUM(link_clicks)           AS link_clicks
  FROM `bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report`
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
  GROUP BY ad_name
)
SELECT
  ad_name,
  spend,
  cv,
  SAFE_DIVIDE(spend, cv)          AS cpa,
  SAFE_DIVIDE(cv, link_clicks)    AS cvr
FROM agg
WHERE spend >= 10000
ORDER BY cpa ASC
```

### デモグラ別CVR（年齢帯分析）

```sql
WITH agg AS (
  SELECT
    age,
    ad_name,
    SUM(spend)       AS spend,
    SUM(purchase)    AS purchase,
    SUM(link_clicks) AS link_clicks
  FROM `bigquery-jukust.dataset.v_CA_meta_ads_demographics_report_with_scenario`
  WHERE
    date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
    AND age = '25-34'   -- 主力ターゲット年齢帯
  GROUP BY age, ad_name
)
SELECT
  *,
  SAFE_DIVIDE(purchase, link_clicks) AS cvr
FROM agg
WHERE link_clicks > 0
ORDER BY cvr DESC
```

---

## よくあるエラーと対処

| エラー | 原因 | 対処 |
|---|---|---|
| `Aggregations of aggregations are not allowed` | ビューに直接GROUP BY+HAVING | CTEパターンに書き直す |
| `ZeroDivisionError` | リンククリック0 | `SAFE_DIVIDE`を使う |
| `UnicodeEncodeError` | 日本語を端末に出力 | CSVに書き出す（`encoding='utf-8-sig'`） |
| `db_dtypes not found` | パッケージ不足 | `pip install db-dtypes pyarrow` |
