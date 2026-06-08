# BigQueryのSTシナリオビューを探してシナリオ内容を取得
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

# --- データセット一覧 ---
print("=== データセット一覧 ===")
datasets = list(client.list_datasets())
for ds in datasets:
    print(f"  {ds.dataset_id}")

# --- STに関連するビュー/テーブルを探す ---
print()
print("=== ST関連のビュー/テーブル ===")
for ds in datasets:
    tables = list(client.list_tables(ds.dataset_id))
    for t in tables:
        if 'ST' in t.table_id or 'st' in t.table_id.lower():
            print(f"  {ds.dataset_id}.{t.table_id}  ({t.table_type})")

print()
print("=== scenario を含むビュー/テーブル ===")
for ds in datasets:
    tables = list(client.list_tables(ds.dataset_id))
    for t in tables:
        if 'scenario' in t.table_id.lower():
            print(f"  {ds.dataset_id}.{t.table_id}  ({t.table_type})")
