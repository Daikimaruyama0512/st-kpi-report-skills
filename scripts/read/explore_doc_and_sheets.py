# 必要: pip install google-auth google-auth-oauthlib google-auth-httplib2
import sys, io, os, json, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
CREDS_FILE = r"/Users/119322/claude-code-template_af/secrets/credentials.json"

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

DOC_ID = "1CNita-zx0q_jz4Mv_FxoKErITvokUoTWzATzZHCWBro"

# --- 認証 ---
creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    else:
        print("ERROR: token.json が無効です。再認証が必要です。")
        sys.exit(1)

token = creds.token

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

# --- ドキュメント読み取り ---
print("=" * 60)
print("【対象ドキュメント の構造】")
print("=" * 60)

doc = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
print(f"タイトル: {doc.get('title', '(不明)')}")
print()

# 見出しと本文テキストを抽出
headings = []
full_text_parts = []

for elem in doc.get('body', {}).get('content', []):
    para = elem.get('paragraph')
    if not para:
        continue
    style = para.get('paragraphStyle', {}).get('namedStyleType', '')
    text_parts = []
    for run in para.get('elements', []):
        t = run.get('textRun', {}).get('content', '')
        text_parts.append(t)
    text = ''.join(text_parts).rstrip('\n')
    if not text.strip():
        continue
    full_text_parts.append(text)
    if 'HEADING' in style:
        headings.append((style, text))

print("【見出し一覧】")
for style, h in headings:
    level = style.replace('HEADING_', 'H')
    indent = "  " * (int(style[-1]) - 1) if style[-1].isdigit() else ""
    print(f"  {indent}[{level}] {h}")

print()
print("【全文（先頭2000字）】")
full_text = '\n'.join(full_text_parts)
print(full_text[:2000])
if len(full_text) > 2000:
    print(f"\n... (以下省略: 全{len(full_text)}字)")

# --- Drive内スプレッドシート検索 ---
print()
print("=" * 60)
print("【Google Drive スプレッドシート検索】")
print("=" * 60)

search_keywords = ["塾講師", "ST", "広告", "実績", "CPA", "応募", "採用", "レポート"]

found_sheets = {}

for keyword in search_keywords:
    q = urllib.parse.quote(f"mimeType='application/vnd.google-apps.spreadsheet' and name contains '{keyword}' and trashed=false")
    url = f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id,name,mimeType,modifiedTime)&pageSize=30"
    result = api_get(url)
    for f in result.get('files', []):
        fid = f['id']
        if fid not in found_sheets:
            found_sheets[fid] = {
                'id': fid,
                'name': f['name'],
                'modifiedTime': f.get('modifiedTime', '')[:10],
                'keywords': []
            }
        found_sheets[fid]['keywords'].append(keyword)

if found_sheets:
    sheets_list = sorted(found_sheets.values(), key=lambda x: x['modifiedTime'], reverse=True)
    print(f"\n合計 {len(sheets_list)} 件のスプレッドシートが見つかりました:\n")
    for i, s in enumerate(sheets_list, 1):
        kw = ', '.join(s['keywords'])
        print(f"  [{i:02d}] {s['name']}")
        print(f"       ID: {s['id']}")
        print(f"       更新日: {s['modifiedTime']}  キーワード: {kw}")
        print()
else:
    print("スプレッドシートが見つかりませんでした。")

print("=" * 60)
print("完了: 上記シートの中から使用するものを選択してください")
print("=" * 60)
