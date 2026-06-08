# ST TOP10クリエイティブ表を追加
import sys, io, os, json, urllib.request, urllib.parse

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

def api_post(url, body):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(
        url, data=data,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

top10_rows = [
    ["広告名（ST）", "広告費(円)", "CV数", "CPA(円)", "CVR(%)"],
    ["02単願_塾バイト探しキャンセル界隈_ブランド診断_新規", "872,427", "0*", "-", "0"],
    ["02単願_失敗したくないなら診断_気軽に診断_横展開", "859,798", "0*", "-", "0"],
    ["01タイパ_効率よく探せる_ブランド診断", "769,764", "0*", "-", "0"],
    ["02単願_性格に合う_ブランド診断", "722,924", "0*", "-", "0"],
    ["01タイパ_受験経験をお金に_ブランド診断_新規", "714,140", "0*", "-", "0"],
    ["02単願_経験を資産に_ブランド診断_横展開", "626,479", "0*", "-", "0"],
    ["01タイパ_指導に集中_ブランド診断", "553,766", "0*", "-", "0"],
    ["ASC_動画_UGC113", "374,955", "0*", "-", "0"],
    ["02単願_性格に合う_16タイプ診断", "344,592", "0*", "-", "0"],
    ["01タイパ_教えることで理解が深まる_ブランド診断_新規", "341,327", "0*", "-", "0"],
]

# 末尾インデックス取得
doc = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body = doc.get('body', {}).get('content', [])
end_index = body[-1].get('endIndex', 1) - 1
print(f"現在の末尾インデックス: {end_index}")

# 改行 + 表を挿入
api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": [{"insertText": {"location": {"index": end_index}, "text": "\n\n"}}]}
)

doc2 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body2 = doc2.get('body', {}).get('content', [])
end2 = body2[-1].get('endIndex', 1) - 1

api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": [{"insertTable": {"rows": len(top10_rows), "columns": len(top10_rows[0]), "location": {"index": end2}}}]}
)
print("TOP10表枠を挿入")

# テーブルのセルを取得
doc3 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
all_tables = [e for e in doc3.get('body', {}).get('content', []) if 'table' in e]
print(f"テーブル数: {len(all_tables)}")

# 最後のテーブル（= TOP10表）を取得
target = all_tables[-1]
tbl = target['table']

# セル挿入リストを逆順（後ろから）で構築
insertions = []
for r_idx, row_data in enumerate(top10_rows):
    if r_idx >= len(tbl.get('tableRows', [])):
        break
    row = tbl['tableRows'][r_idx]
    for c_idx, cell_text in enumerate(row_data):
        if c_idx >= len(row.get('tableCells', [])):
            break
        cell = row['tableCells'][c_idx]
        cell_content = cell.get('content', [])
        if cell_content:
            para_start = cell_content[0].get('startIndex', 0)
            insertions.append({'index': para_start, 'text': cell_text, 'r': r_idx, 'c': c_idx})

insertions.sort(key=lambda x: x['index'], reverse=True)
print(f"{len(insertions)}セルを書き込みます...")

for ins in insertions:
    try:
        api_post(
            f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
            {"requests": [{"insertText": {"location": {"index": ins['index']}, "text": ins['text']}}]}
        )
    except Exception as e:
        print(f"  ERROR at cell[{ins['r']}][{ins['c']}] index={ins['index']}: {e}")
        break

print("TOP10表書き込み完了")
print(f"\n完了: https://docs.google.com/document/d/{DOC_ID}/edit")
