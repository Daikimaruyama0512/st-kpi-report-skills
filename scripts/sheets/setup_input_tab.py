# ST_KPI報告シートに「入力」タブを追加するセットアップスクリプト
# 1回だけ実行すればOK。既にタブがある場合はスキップする。
#
# 「入力」タブの構造:
#   A: 月ラベル（例: 5月）
#   B: 月間予算（例: 2000000）
#   C: LINE登録CV目標（例: 500）
#   D: 応募CV（custom_cv_2がない場合の手動入力欄）
#
# 必要: pip install google-api-python-client google-auth

import sys
import io
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
SPREADSHEET_ID = '1xXeCl4Xbkxz-w_jT49TmA3-voruL2cTbF1f308hZ5vQ'
TAB_NAME = '入力'

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

service = build('sheets', 'v4', credentials=creds)

# ========== 既存タブ確認 ==========
ss_meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
existing_sheets = [s['properties']['title'] for s in ss_meta['sheets']]

if TAB_NAME in existing_sheets:
    print(f"「{TAB_NAME}」タブは既に存在します。スキップします。")
    print(f"既存タブ: {existing_sheets}")
    sys.exit(0)

print(f"「{TAB_NAME}」タブを追加します...")

# ========== タブ追加 ==========
add_sheet_req = {
    'addSheet': {
        'properties': {
            'title': TAB_NAME,
            'gridProperties': {
                'rowCount': 30,
                'columnCount': 6,
            }
        }
    }
}
result = service.spreadsheets().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
    body={'requests': [add_sheet_req]}
).execute()
new_sheet_id = result['replies'][0]['addSheet']['properties']['sheetId']
print(f"タブ追加完了（sheetId: {new_sheet_id}）")

# ========== ヘッダーとサンプルデータを書き込み ==========
today = date.today()

# 3ヶ月分の月ラベル行を用意
def prev_month(y, m, delta):
    m -= delta
    while m <= 0:
        m += 12
        y -= 1
    return y, m

months = [
    prev_month(today.year, today.month, 2),
    prev_month(today.year, today.month, 1),
    (today.year, today.month),
]

values = [
    # ヘッダー行
    ['月', '月間予算', 'LINE登録CV目標', '応募CV（BQにない場合）', '（応募CV目標）', '備考'],
]
for y, m in months:
    values.append([f'{m}月', '', '', '', '', ''])

# 現在月のサンプルは予算2,000,000を入れておく
values[-1][1] = 2000000  # 月間予算

service.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=f"'{TAB_NAME}'!A1",
    valueInputOption='USER_ENTERED',
    body={'values': values}
).execute()

# ========== 書式設定（ヘッダー行を太字・背景色）==========
format_req = {
    'repeatCell': {
        'range': {
            'sheetId': new_sheet_id,
            'startRowIndex': 0,
            'endRowIndex': 1,
            'startColumnIndex': 0,
            'endColumnIndex': 6,
        },
        'cell': {
            'userEnteredFormat': {
                'backgroundColor': {'red': 0.27, 'green': 0.42, 'blue': 0.66},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
            }
        },
        'fields': 'userEnteredFormat(backgroundColor,textFormat)',
    }
}
service.spreadsheets().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
    body={'requests': [format_req]}
).execute()

print(f"\n完了！")
print(f"スプレッドシート: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
print(f"\n「入力」タブに以下を記入してください:")
print(f"  B列: 月間予算（例: 2000000）")
print(f"  C列: LINE登録CV目標（例: 500）")
print(f"  D列: 応募CV実績（BigQueryのcustom_cv_2がない場合のみ必要）")
print(f"\nその後 python scripts/kpi_report_st.py で動作確認してください。")
