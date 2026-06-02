# テーブルセルにデータを書き込むスクリプト（インデックス修正版）
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
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"  HTTPError {e.code}: {err_body[:300]}")
        raise

def get_all_tables(doc):
    """ドキュメント内の全テーブルを取得（インデックス順）"""
    tables = []
    for elem in doc.get('body', {}).get('content', []):
        if 'table' in elem:
            tables.append(elem)
    return tables

def collect_cell_insertions(table, data_rows):
    """テーブルのセル挿入リクエストを収集（後ろのセルから順に）"""
    insertions = []
    tbl = table['table']
    for r_idx, row_data in enumerate(data_rows):
        if r_idx >= len(tbl.get('tableRows', [])):
            break
        table_row = tbl['tableRows'][r_idx]
        for c_idx, cell_text in enumerate(row_data):
            if c_idx >= len(table_row.get('tableCells', [])):
                break
            cell = table_row['tableCells'][c_idx]
            cell_content = cell.get('content', [])
            if cell_content:
                # paraStart を直接使用（+1不要）
                para_start = cell_content[0].get('startIndex', 0)
                insertions.append({
                    'index': para_start,
                    'text': cell_text,
                    'row': r_idx,
                    'col': c_idx
                })
    # 高インデックス順にソート（後ろから挿入してインデックスズレを防ぐ）
    insertions.sort(key=lambda x: x['index'], reverse=True)
    return insertions

# データ定義
kpi_summary_rows = [
    ["サービス", "広告費(円)", "CV数", "CPA(円)", "CTR(%)", "CPM(円)", "CPC(円)"],
    ["CA", "28,228,580", "3,967", "7,116", "0.40", "1,405", "354"],
    ["ST", "13,668,909", "19", "719,416*", "0.35", "711", "206"],
    ["合計", "41,897,489", "3,986", "10,511", "0.37", "1,066", "287"],
]

# ドキュメント取得
doc = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
tables = get_all_tables(doc)
print(f"テーブル数: {len(tables)}")

for i, tbl in enumerate(tables):
    tbl_data = tbl['table']
    print(f"  Table[{i}]: rows={tbl_data.get('rows')}, cols={tbl_data.get('columns')}, start={tbl.get('startIndex')}")

if len(tables) >= 1:
    print()
    print("=== KPIサマリー表（Table[0]）にデータを書き込み ===")
    insertions = collect_cell_insertions(tables[0], kpi_summary_rows)
    print(f"  {len(insertions)}セルを書き込みます...")

    # 1リクエストずつ送信（デバッグしやすいように）
    for ins in insertions:
        try:
            api_post(
                f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
                {"requests": [{"insertText": {"location": {"index": ins['index']}, "text": ins['text']}}]}
            )
        except Exception as e:
            print(f"  ERROR at cell[{ins['row']}][{ins['col']}] index={ins['index']}: {e}")
            break

    print("  KPIサマリー表書き込み完了")

print()
print(f"完了: https://docs.google.com/document/d/{DOC_ID}/edit")
