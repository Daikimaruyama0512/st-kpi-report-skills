# TOP10表をシナリオ付き表に差し替え
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

# BigQueryからシナリオ取得
from google.cloud import bigquery
PROJECT_ID = "bigquery-jukust"
bq_creds = Credentials.from_authorized_user_file(TOKEN_FILE, ['https://www.googleapis.com/auth/bigquery'])
if bq_creds.expired and bq_creds.refresh_token:
    bq_creds.refresh(Request())
bq = bigquery.Client(project=PROJECT_ID, credentials=bq_creds)

scenario_map = {}
q = "SELECT ad_name, scenario FROM `bigquery-jukust.ST_meta_raw.ST_meta_scenario_sync`"
for row in bq.query(q).result():
    scenario_map[row.ad_name] = row.scenario

# TOP10広告データ（順序維持）
top10_data = [
    ("02単願_塾バイト探しキャンセル界隈_ブランド診断_新規", "872,427"),
    ("02単願_失敗したくないなら診断_気軽に診断_横展開", "859,798"),
    ("01タイパ_効率よく探せる_ブランド診断", "769,764"),
    ("02単願_性格に合う_ブランド診断", "722,924"),
    ("01タイパ_受験経験をお金に_ブランド診断_新規", "714,140"),
    ("02単願_経験を資産に_ブランド診断_横展開", "626,479"),
    ("01タイパ_指導に集中_ブランド診断", "553,766"),
    ("ASC_動画_UGC113", "374,955"),
    ("02単願_性格に合う_16タイプ診断", "344,592"),
    ("01タイパ_教えることで理解が深まる_ブランド診断_新規", "341,327"),
]

# 表データ作成（ヘッダー + 10行）
table_data = [["広告名（ST）", "広告費(円)", "シナリオ内容"]]
for ad_name, spend in top10_data:
    scenario = scenario_map.get(ad_name, "（シナリオデータなし）")
    # 改行を除去して1セルに収める
    scenario_clean = scenario.replace('\n', ' ').strip()
    table_data.append([ad_name, spend, scenario_clean])

# --- 現在のドキュメント構造取得 ---
doc = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body_items = doc.get('body', {}).get('content', [])
tables = [e for e in body_items if 'table' in e]
print(f"テーブル数: {len(tables)}")

if len(tables) < 2:
    print("ERROR: TOP10表が見つかりません")
    sys.exit(1)

# 2番目の表（TOP10）を削除
top10_table = tables[1]
tbl_start = top10_table['startIndex']
tbl_end = top10_table['endIndex']
print(f"TOP10表の範囲: start={tbl_start}, end={tbl_end}")

# 削除
api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": [{"deleteContentRange": {"range": {"startIndex": tbl_start, "endIndex": tbl_end}}}]}
)
print("旧TOP10表を削除")

# 削除後の末尾インデックス取得
doc2 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body2 = doc2.get('body', {}).get('content', [])
end2 = body2[-1].get('endIndex', 1) - 1
print(f"削除後の末尾インデックス: {end2}")

# 新しい表を挿入（3列: 広告名 / 広告費 / シナリオ）
api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": [{"insertTable": {
        "rows": len(table_data),
        "columns": 3,
        "location": {"index": end2}
    }}]}
)
print(f"新しい3列表を挿入（{len(table_data)}行）")

# セルデータ書き込み
doc3 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body3 = doc3.get('body', {}).get('content', [])
tables3 = [e for e in body3 if 'table' in e]
new_table = tables3[-1]
tbl = new_table['table']

insertions = []
for r_idx, row_data in enumerate(table_data):
    if r_idx >= len(tbl.get('tableRows', [])):
        break
    tbl_row = tbl['tableRows'][r_idx]
    for c_idx, cell_text in enumerate(row_data):
        if c_idx >= len(tbl_row.get('tableCells', [])):
            break
        cell = tbl_row['tableCells'][c_idx]
        cell_content = cell.get('content', [])
        if cell_content:
            para_start = cell_content[0].get('startIndex', 0)
            insertions.append({'index': para_start, 'text': cell_text, 'r': r_idx, 'c': c_idx})

# 高インデックス順にソートして書き込み
insertions.sort(key=lambda x: x['index'], reverse=True)
print(f"{len(insertions)}セルを書き込みます...")

for ins in insertions:
    try:
        api_post(
            f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
            {"requests": [{"insertText": {"location": {"index": ins['index']}, "text": ins['text']}}]}
        )
    except Exception as e:
        print(f"  ERROR at cell[{ins['r']}][{ins['c']}] idx={ins['index']}: {e}")

print("シナリオ付きTOP10表の書き込み完了")
print(f"\n完了: https://docs.google.com/document/d/{DOC_ID}/edit")
