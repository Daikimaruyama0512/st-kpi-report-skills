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
    'https://www.googleapis.com/auth/calendar.events',
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

def get_sheet_tabs(sheet_id):
    """スプレッドシートのシートタブ一覧を取得"""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=sheets.properties"
    data = api_get(url)
    return [s['properties'] for s in data.get('sheets', [])]

def get_sheet_values(sheet_id, range_str):
    """指定範囲の値を取得"""
    encoded_range = urllib.parse.quote(range_str)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{encoded_range}"
    data = api_get(url)
    return data.get('values', [])

# 対象シートの定義
SHEETS = {
    "MBO草案": "1CvCOH7tQy5l6Uab9m0zvj4f8ch-I2cd3BVgP8U3xfq4",
    "KPI報告(4/1-4/7)": "1HUBihdlWltffP_QIg6fR19T_1LOy6bZvmQZZ301vkE4",
    "ST広告運用": "1JryXlfrMvw9YDZoLYFpCeOoKbQxcYeuYOJ8rg2mgDJU",
}

for sheet_name, sheet_id in SHEETS.items():
    print("=" * 70)
    print(f"【{sheet_name}】 ID: {sheet_id}")
    print("=" * 70)

    try:
        tabs = get_sheet_tabs(sheet_id)
        print(f"シートタブ ({len(tabs)}枚):")
        for t in tabs:
            print(f"  - [{t['index']+1}] {t['title']}  (行数: {t.get('gridProperties', {}).get('rowCount','?')}, 列数: {t.get('gridProperties', {}).get('columnCount','?')})")
        print()

        # 最初のシートを読む
        first_tab = tabs[0]['title'] if tabs else "Sheet1"
        values = get_sheet_values(sheet_id, f"'{first_tab}'!A1:Z50")
        print(f"「{first_tab}」の内容（先頭50行）:")
        for i, row in enumerate(values[:50], 1):
            row_str = '\t'.join(str(c) for c in row)
            print(f"  {i:2d}: {row_str}")
        print()

    except Exception as e:
        print(f"  ERROR: {e}")
        print()

print("=" * 70)
print("読み取り完了")
print("=" * 70)
