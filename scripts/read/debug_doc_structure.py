# ドキュメント構造確認スクリプト
import sys, io, os, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

DOC_ID = "1CNita-zx0q_jz4Mv_FxoKErITvokUoTWzATzZHCWBro"

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

doc = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body_content = doc.get('body', {}).get('content', [])

print(f"タイトル: {doc.get('title')}")
print(f"body要素数: {len(body_content)}")
print()

# 末尾の要素を確認
for i, elem in enumerate(body_content[-10:], len(body_content)-10):
    elem_type = "table" if "table" in elem else ("paragraph" if "paragraph" in elem else "other")
    start = elem.get("startIndex", "?")
    end = elem.get("endIndex", "?")
    print(f"[{i}] type={elem_type}, start={start}, end={end}")

    if "table" in elem:
        tbl = elem["table"]
        print(f"  rows={tbl.get('rows')}, cols={tbl.get('columns')}")
        for r_idx, row in enumerate(tbl.get("tableRows", [])[:3]):
            for c_idx, cell in enumerate(row.get("tableCells", [])[:3]):
                cell_content = cell.get("content", [])
                if cell_content:
                    para_start = cell_content[0].get("startIndex", "?")
                    para_end = cell_content[0].get("endIndex", "?")
                    print(f"    cell[{r_idx}][{c_idx}] paraStart={para_start} paraEnd={para_end}")
