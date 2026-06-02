# STシナリオをBigQueryから取得してCSVに保存
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/drive',
]
PROJECT_ID = "bigquery-jukust"

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

client = bigquery.Client(project=PROJECT_ID, credentials=creds)

# --- ST_meta_scenario_sync のスキーマ確認 ---
print("=== ST_meta_scenario_sync スキーマ ===")
table = client.get_table("bigquery-jukust.ST_meta_raw.ST_meta_scenario_sync")
for field in table.schema:
    print(f"  {field.name}: {field.field_type}")

# --- 先頭3件サンプル確認 ---
print()
print("=== サンプルデータ（先頭3件）===")
q = "SELECT * FROM `bigquery-jukust.ST_meta_raw.ST_meta_scenario_sync` LIMIT 3"
rows = client.query(q).result()
for row in rows:
    print(dict(row))

# --- 対象広告名のシナリオを取得 ---
print()
print("=== TOP10広告のシナリオ取得 ===")

target_ads = [
    "02単願_塾バイト探しキャンセル界隈_ブランド診断_新規",
    "02単願_失敗したくないなら診断_気軽に診断_横展開",
    "01タイパ_効率よく探せる_ブランド診断",
    "02単願_性格に合う_ブランド診断",
    "01タイパ_受験経験をお金に_ブランド診断_新規",
    "02単願_経験を資産に_ブランド診断_横展開",
    "01タイパ_指導に集中_ブランド診断",
    "ASC_動画_UGC113",
    "02単願_性格に合う_16タイプ診断",
    "01タイパ_教えることで理解が深まる_ブランド診断_新規",
]

# まずシナリオテーブルの全ad_nameを確認
q_all = """
SELECT DISTINCT ad_name
FROM `bigquery-jukust.ST_meta_raw.ST_meta_scenario_sync`
ORDER BY ad_name
"""
all_names = [row.ad_name for row in client.query(q_all).result()]
print(f"シナリオテーブルの広告名数: {len(all_names)}")
print("先頭20件:")
for n in all_names[:20]:
    print(f"  {n}")
