import sys, io, json, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token
SHEET_ID = "1YBomNUAvx9fDhGH4pjVuVlQcpK5Er4FTSFa_BcJvlrA"
TARGET_GID = "1732572281"

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

# タブ一覧を取得してgidに対応するタブ名を探す
meta = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets.properties")
tabs = meta['sheets']

print("=== タブ一覧 ===")
target_tab = None
for s in tabs:
    p = s['properties']
    gid = str(p.get('sheetId', ''))
    title = p.get('title', '')
    print(f"  gid={gid}  title={title}")
    if gid == TARGET_GID:
        target_tab = title

print(f"\n対象タブ: {target_tab}")

if not target_tab:
    print("対象タブが見つかりませんでした。")
    sys.exit(1)

# シート全体を取得
encoded = urllib.parse.quote(f"'{target_tab}'!A1:Z200")
data = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}?valueRenderOption=FORMATTED_VALUE")
rows = data.get('values', [])

print(f"\n=== {target_tab} 全行データ ===")
for i, row in enumerate(rows):
    if any(str(c).strip() for c in row):
        print(f"  行{i+1}: {[str(c)[:60] for c in row]}")
