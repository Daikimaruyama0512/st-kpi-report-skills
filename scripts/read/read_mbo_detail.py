# 必要: pip install google-auth google-auth-oauthlib
import sys, io, os, json, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

def get_values(sheet_id, tab_name, cell_range="A1:P60"):
    encoded = urllib.parse.quote(f"'{tab_name}'!{cell_range}")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{encoded}"
    data = api_get(url)
    return data.get('values', [])

# --- 1. 丸山草案タブ ---
MBO_ID = "1CvCOH7tQy5l6Uab9m0zvj4f8ch-I2cd3BVgP8U3xfq4"
KPI_ID = "1HUBihdlWltffP_QIg6fR19T_1LOy6bZvmQZZ301vkE4"

print("=" * 70)
print("【丸山 草案タブ】")
print("=" * 70)
vals = get_values(MBO_ID, "丸山　草案")
for i, row in enumerate(vals, 1):
    row_str = '\t'.join(str(c) for c in row)
    print(f"  {i:2d}: {row_str}")

print()
print("=" * 70)
print("【KPI報告 - ST日次タブ】")
print("=" * 70)
vals = get_values(KPI_ID, "ST日次", "A1:J30")
for i, row in enumerate(vals, 1):
    row_str = '\t'.join(str(c) for c in row)
    print(f"  {i:2d}: {row_str}")

print()
print("=" * 70)
print("【KPI報告 - 広告別TOP20タブ】")
print("=" * 70)
vals = get_values(KPI_ID, "広告別TOP20", "A1:K30")
for i, row in enumerate(vals, 1):
    row_str = '\t'.join(str(c) for c in row)
    print(f"  {i:2d}: {row_str}")

print()
print("=" * 70)
print("【KPI報告 - CA日次タブ（先頭20行）】")
print("=" * 70)
vals = get_values(KPI_ID, "CA日次", "A1:J20")
for i, row in enumerate(vals, 1):
    row_str = '\t'.join(str(c) for c in row)
    print(f"  {i:2d}: {row_str}")
