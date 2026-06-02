# 対象シートの値・数式・メタデータを読み取る調査スクリプト
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
SHEET_ID = "18Y7A7HJWwOguajbKLS65nxPfJUcxTCDX-_TCiZvJVvs"
TARGET_GID = 1951094858

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

# 1. スプレッドシート全体のメタデータ取得
print("=" * 60)
print("1. シートタブ一覧")
print("=" * 60)
meta = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=properties.title,sheets.properties")
print(f"スプレッドシート名: {meta['properties']['title']}")
tab_name = None
for s in meta['sheets']:
    p = s['properties']
    gid = p.get('sheetId')
    mark = " ← 対象" if gid == TARGET_GID else ""
    print(f"  gid={gid}  '{p['title']}'{mark}")
    if gid == TARGET_GID:
        tab_name = p['title']

print(f"\n対象タブ: {tab_name}")

# 2. 対象範囲の値を取得（FORMATTED_VALUE）
print("\n" + "=" * 60)
print("2. A58:AJ122 の値（先頭5行）")
print("=" * 60)
encoded = urllib.parse.quote(f"'{tab_name}'!A58:AJ122")
url_val = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}?valueRenderOption=FORMATTED_VALUE"
data_val = api_get(url_val)
rows_val = data_val.get('values', [])
print(f"取得行数: {len(rows_val)}, 最大列数: {max((len(r) for r in rows_val), default=0)}")
for i, row in enumerate(rows_val[:8]):
    print(f"  行{58+i}: {row}")

# 3. 対象範囲の数式を取得（FORMULA）
print("\n" + "=" * 60)
print("3. A58:AJ122 の数式（非空のセルのみ・先頭8行）")
print("=" * 60)
url_fml = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}?valueRenderOption=FORMULA"
data_fml = api_get(url_fml)
rows_fml = data_fml.get('values', [])
for i, row in enumerate(rows_fml[:8]):
    non_empty = [(j, cell) for j, cell in enumerate(row) if cell and str(cell).startswith('=')]
    if non_empty:
        for j, cell in non_empty:
            col_letter = chr(ord('A') + j) if j < 26 else chr(ord('A') + j//26 - 1) + chr(ord('A') + j%26)
            print(f"  {col_letter}{58+i}: {cell}")

# 4. シート全体の先頭57行も確認（ヘッダー等）
print("\n" + "=" * 60)
print("4. A1:AJ57 の値（先頭10行）")
print("=" * 60)
encoded2 = urllib.parse.quote(f"'{tab_name}'!A1:AJ57")
data_top = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded2}?valueRenderOption=FORMATTED_VALUE")
rows_top = data_top.get('values', [])
print(f"取得行数: {len(rows_top)}")
for i, row in enumerate(rows_top[:10]):
    if any(c for c in row):
        print(f"  行{i+1}: {row}")

# 5. 他シートの参照を調べる（数式内の他シート参照）
print("\n" + "=" * 60)
print("5. 数式内で参照されている他シート名")
print("=" * 60)
all_formulas = []
for row in rows_fml:
    for cell in row:
        if cell and str(cell).startswith('='):
            all_formulas.append(str(cell))

import re
refs = set()
for f in all_formulas:
    # 'SheetName'!A1 or SheetName!A1 パターン
    matches = re.findall(r"'([^']+)'!", f)
    matches += re.findall(r"(?<!')\b([A-Za-z][A-Za-z0-9_\u3040-\u9fff\u30A0-\u30FF\u4E00-\u9FFF]*)!", f)
    refs.update(matches)

# 対象タブ自身は除外
refs.discard(tab_name)
if refs:
    for r in sorted(refs):
        print(f"  参照先: '{r}'")
else:
    print("  他シート参照なし（同シート内完結 or 外部データ）")

# 6. 参照先シートの先頭3行を確認
print("\n" + "=" * 60)
print("6. 参照先シートのサンプル（先頭3行）")
print("=" * 60)
tab_names_all = [s['properties']['title'] for s in meta['sheets']]
for ref in refs:
    if ref in tab_names_all:
        enc_ref = urllib.parse.quote(f"'{ref}'!A1:Z3")
        try:
            d = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc_ref}?valueRenderOption=FORMATTED_VALUE")
            print(f"\n  [{ref}]")
            for row in d.get('values', []):
                print(f"    {row}")
        except Exception as e:
            print(f"  [{ref}] 読み取りエラー: {e}")

print("\n完了")
