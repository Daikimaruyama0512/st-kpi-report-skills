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

# --- ドキュメントの末尾インデックスを取得 ---
doc = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body_content = doc.get('body', {}).get('content', [])
end_index = body_content[-1].get('endIndex', 1) - 1  # 末尾の\nの手前

print(f"ドキュメント「{doc.get('title')}」末尾インデックス: {end_index}")

# --- 挿入するテキストブロックを組み立て ---
# 末尾から逆順に挿入（インデックスのズレを防ぐため）

# 表データの定義
kpi_summary_rows = [
    ["サービス", "広告費(円)", "CV数", "CPA(円)", "CTR(%)", "CPM(円)", "CPC(円)"],
    ["CA", "28,228,580", "3,967", "7,116", "0.40", "1,405", "354"],
    ["ST", "13,668,909", "19", "719,416*", "0.35", "711", "206"],
    ["合計", "41,897,489", "3,986", "10,511", "0.37", "1,066", "287"],
]

top20_rows = [
    ["広告名", "広告費(円)", "CV数", "CPA(円)", "CVR(%)"],
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

# --- テキスト挿入（末尾に追記）---
# Step 1: セクションヘッダーのテキストをまとめて挿入
section_text = (
    "\n\n"
    "【定量的裏付けデータ】（Google Driveシートより自動取得 2026-04-19）\n"
    "\n"
    "■ FY26上期 チームKPI目標\n"
    "面談目標: 249件 ／ 採用目標: 1,278件\n"
    "\n"
    "■ 丸山 MBOテーマと定量目標\n"
    "4月テーマ: LINE×LPの訴求一貫性\n"
    "  WHY: LINE登録CVR向上のため、ターゲティング精度向上によりCVRを向上させることができるため\n"
    "  WHAT: 遷移先のLINEの訴求内容と広告での訴求内容に一貫性を持たせる\n"
    "  HOW: LINE登録担当に働きかけ、カスタマージャーニーの一貫性を担保する\n"
    "\n"
    "5月テーマ: 訴求軸の体系化とシナリオドリブン広告運用\n"
    "  WHY: 広告シナリオとCVRの相関を明確にし、次の施策に活かすため\n"
    "  WHAT: STシナリオ別CPAの可視化、PASONA法則に基づく新規クリエイティブ5本制作\n"
    "  HOW: BigQueryのシナリオビューを活用した月次分析レポート作成（毎月15日提出・Slack共有）\n"
    "  定性目標: BigQueryを活用したシナリオ分析レポートを月次で作成・共有\n"
    "\n"
    "■ 直近週次実績（2026/4/1〜4/7、参考値）\n"
    "※ ST CVは面談申込まで中央値40日ラグ → 週次CV数は過小評価\n"
    "\n"
    "■ ST 出稿中クリエイティブ TOP10（4/1〜4/7）\n"
    "※ CV=0はすべて40日ラグによる過小評価（実際の成果は今後のBigQueryで確認要）\n"
)

# まず末尾にテキストを挿入
requests_1 = [
    {
        "insertText": {
            "location": {"index": end_index},
            "text": section_text
        }
    }
]

result1 = api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": requests_1}
)
print("テキスト挿入完了")

# 挿入後のドキュメントを再取得してインデックスを更新
doc2 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body_content2 = doc2.get('body', {}).get('content', [])
new_end_index = body_content2[-1].get('endIndex', 1) - 1

# --- 表1: KPIサマリー を挿入 ---
# KPIサマリー表の位置（"■ 直近週次実績"の後）
# 現在のnew_end_indexの手前に表を挿入

# 表の挿入（末尾に）
table_rows_1 = len(kpi_summary_rows)
table_cols_1 = len(kpi_summary_rows[0])

requests_2 = [
    {
        "insertTable": {
            "rows": table_rows_1,
            "columns": table_cols_1,
            "location": {"index": new_end_index}
        }
    }
]
result2 = api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": requests_2}
)
print("KPIサマリー表枠挿入完了")

# 表にデータを書き込む（再取得してインデックスを特定）
doc3 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")

# 表のセルを特定してテキストを書き込む
table_requests = []
body_items = doc3.get('body', {}).get('content', [])

# 末尾の表を探す
target_table = None
for item in reversed(body_items):
    if 'table' in item:
        target_table = item
        break

if target_table:
    table = target_table['table']
    for r_idx, row_data in enumerate(kpi_summary_rows):
        table_row = table['tableRows'][r_idx]
        for c_idx, cell_text in enumerate(row_data):
            cell = table_row['tableCells'][c_idx]
            cell_content = cell.get('content', [])
            if cell_content:
                cell_start = cell_content[0].get('startIndex', 0) + 1
                table_requests.append({
                    "insertText": {
                        "location": {"index": cell_start},
                        "text": cell_text
                    }
                })

    # ヘッダー行に太字
    # 逆順に処理済みのため順序注意 → insertTextは逆順に実行する必要がある
    table_requests_reversed = list(reversed(table_requests))

    # 50件ずつバッチ処理
    batch_size = 40
    for i in range(0, len(table_requests_reversed), batch_size):
        batch = table_requests_reversed[i:i+batch_size]
        api_post(
            f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
            {"requests": batch}
        )
    print(f"KPIサマリー表データ書き込み完了（{len(table_requests)}セル）")

# --- 表2: ST TOP10クリエイティブ を末尾に挿入 ---
doc4 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body4 = doc4.get('body', {}).get('content', [])
end4 = body4[-1].get('endIndex', 1) - 1

# TOP10テーブル追加前に改行テキストを挿入
pre_text = "\n\n"
api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": [{"insertText": {"location": {"index": end4}, "text": pre_text}}]}
)

doc5 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body5 = doc5.get('body', {}).get('content', [])
end5 = body5[-1].get('endIndex', 1) - 1

table_rows_2 = len(top20_rows)
table_cols_2 = len(top20_rows[0])
api_post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    {"requests": [{"insertTable": {"rows": table_rows_2, "columns": table_cols_2, "location": {"index": end5}}}]}
)
print("TOP10表枠挿入完了")

doc6 = api_get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")
body6 = doc6.get('body', {}).get('content', [])
target_table2 = None
for item in reversed(body6):
    if 'table' in item:
        target_table2 = item
        break

if target_table2:
    table2 = target_table2['table']
    table_requests2 = []
    for r_idx, row_data in enumerate(top20_rows):
        table_row = table2['tableRows'][r_idx]
        for c_idx, cell_text in enumerate(row_data):
            cell = table_row['tableCells'][c_idx]
            cell_content = cell.get('content', [])
            if cell_content:
                cell_start = cell_content[0].get('startIndex', 0) + 1
                table_requests2.append({
                    "insertText": {
                        "location": {"index": cell_start},
                        "text": cell_text
                    }
                })
    table_requests2_rev = list(reversed(table_requests2))
    for i in range(0, len(table_requests2_rev), 40):
        batch = table_requests2_rev[i:i+40]
        api_post(
            f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
            {"requests": batch}
        )
    print(f"TOP10表データ書き込み完了（{len(table_requests2)}セル）")

print()
print(f"完了: https://docs.google.com/document/d/{DOC_ID}/edit")
