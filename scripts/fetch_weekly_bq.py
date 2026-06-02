#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ST Meta広告の直近90日BQデータを取得して weekly_bq_cache.json に保存する。
update_seasonal_insights.py と kpi_report_st.py が共有するデータソース。

使い方:
  python scripts/fetch_weekly_bq.py          # 当日キャッシュがなければ取得
  python scripts/fetch_weekly_bq.py --force  # 強制再取得

必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth
"""

import sys
import io
import os
import json
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
CACHE_FILE = r"/Users/119322/Desktop/claude-code-template_af/scripts/weekly_bq_cache.json"
PROJECT_ID = "bigquery-jukust"
SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]


def is_cache_fresh():
    """当日のキャッシュが存在するか確認する"""
    if not os.path.exists(CACHE_FILE):
        return False
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        return cache.get('fetched_at') == date.today().isoformat()
    except Exception:
        return False


def fetch_and_save():
    """BQからデータを取得してキャッシュに保存する"""
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    client = bigquery.Client(project=PROJECT_ID, credentials=creds)

    query = """
WITH agg AS (
  SELECT
    ad_name,
    ANY_VALUE(scenario)         AS scenario,
    SUM(spend)                  AS spend,
    SUM(complete_registration)  AS cv,
    SUM(link_clicks)            AS link_clicks,
    SUM(impressions)            AS impressions,
    SUM(video_view_3s)          AS video_view_3s,
    SUM(video_p25)              AS video_p25,
    SUM(video_p50)              AS video_p50,
    SUM(video_p75)              AS video_p75,
    SUM(video_p100)             AS video_p100
  FROM `bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report`
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
  GROUP BY ad_name
)
SELECT
  ad_name,
  scenario,
  spend,
  cv,
  link_clicks,
  impressions,
  video_view_3s,
  video_p25,
  video_p50,
  video_p75,
  video_p100,
  SAFE_DIVIDE(spend, cv)                   AS cpa,
  SAFE_DIVIDE(cv, link_clicks)             AS cvr,
  SAFE_DIVIDE(video_view_3s, impressions)  AS rate_3s,
  SAFE_DIVIDE(video_p25, impressions)      AS rate_p25,
  SAFE_DIVIDE(video_p50, impressions)      AS rate_p50,
  SAFE_DIVIDE(video_p75, impressions)      AS rate_p75,
  SAFE_DIVIDE(video_p100, impressions)     AS rate_p100
FROM agg
WHERE spend >= 10000
ORDER BY cpa ASC NULLS LAST
"""
    print("BigQuery クエリ実行中...")
    df = client.query(query).to_dataframe()
    print(f"取得完了: {len(df)} 件（spend>=1万円）")

    # NaN を None に変換してJSON保存
    records = df.where(df.notna(), other=None).to_dict(orient='records')

    cache = {
        'fetched_at': date.today().isoformat(),
        'data': records
    }
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    print(f"キャッシュ保存: {CACHE_FILE}")
    return len(records)


def main():
    force = '--force' in sys.argv
    if not force and is_cache_fresh():
        print(f"当日のキャッシュが既に存在します（{date.today().isoformat()}）。スキップ。")
        print("強制再取得する場合: python scripts/fetch_weekly_bq.py --force")
        return
    count = fetch_and_save()
    print(f"完了: {count} 件")


if __name__ == '__main__':
    main()
