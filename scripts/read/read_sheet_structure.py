# シート構造を要約して出力するスクリプト
import sys, io, json, urllib.request, urllib.parse, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token
SHEET_ID = "18Y7A7HJWwOguajbKLS65nxPfJUcxTCDX-_TCiZvJVvs"
TAB_NAME = "シナリオ"

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

def col_letter(j):
    if j < 26:
        return chr(ord('A') + j)
    return chr(ord('A') + j // 26 - 1) + chr(ord('A') + j % 26)

# A. 値取得（A58:AJ122）
encoded = urllib.parse.quote(f"'{TAB_NAME}'!A58:AJ122")
rows_val = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}?valueRenderOption=FORMATTED_VALUE").get('values', [])

# B. 数式取得（A58:AJ122）
rows_fml = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}?valueRenderOption=FORMULA").get('values', [])

# C. ヘッダー行を取得（A1:AJ57）
enc2 = urllib.parse.quote(f"'{TAB_NAME}'!A1:AJ57")
rows_head = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc2}?valueRenderOption=FORMATTED_VALUE").get('values', [])

print("=== ヘッダー候補（A1:AJ57 の非空行）===")
for i, row in enumerate(rows_head):
    if any(c for c in row):
        short = [str(c)[:30] for c in row[:36]]
        print(f"  行{i+1}: {short}")

print("\n=== A58:AJ122 値（全行）===")
for i, row in enumerate(rows_val):
    short = [str(c)[:20] for c in row]
    print(f"  行{58+i}: {short}")

print("\n=== 数式一覧（ユニーク・最初の出現セルつき）===")
seen = {}
for i, row in enumerate(rows_fml):
    for j, cell in enumerate(row):
        if cell and str(cell).startswith('='):
            # 数式テンプレートを正規化（セル参照を除いた骨格）
            skeleton = re.sub(r'[A-Z]+\d+', 'REF', str(cell))
            if skeleton not in seen:
                seen[skeleton] = f"{col_letter(j)}{58+i}"
                print(f"  {col_letter(j)}{58+i}: {cell}")

print("\n=== 他シート参照 ===")
all_refs = set()
for row in rows_fml:
    for cell in row:
        if cell and '!' in str(cell):
            for m in re.findall(r"'([^']+)'!", str(cell)):
                all_refs.add(m)
            for m in re.findall(r"(?<!['\w])([A-Za-z\u3040-\u9fff\u30A0-\u30FF][A-Za-z0-9_\u3040-\u9fff\u30A0-\u30FF\u4E00-\u9FFF]*)!", str(cell)):
                all_refs.add(m)
all_refs.discard(TAB_NAME)
for r in sorted(all_refs):
    print(f"  '{r}'")

# D. 参照先シートのヘッダー
print("\n=== 参照先シートの先頭3行 ===")
meta = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets.properties")
all_tabs = {s['properties']['title'] for s in meta['sheets']}
for ref in sorted(all_refs):
    if ref in all_tabs:
        enc_r = urllib.parse.quote(f"'{ref}'!A1:Z5")
        try:
            d = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc_r}?valueRenderOption=FORMATTED_VALUE")
            print(f"\n  [{ref}]")
            for row in d.get('values', [])[:5]:
                print(f"    {[str(c)[:25] for c in row]}")
        except Exception as e:
            print(f"  [{ref}] エラー: {e}")

print("\n完了")
