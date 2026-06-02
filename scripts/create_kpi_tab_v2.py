# ST_KPI報告シートに「ST_KPI報告_v2」タブを追加するスクリプト
# 集計さんシートのKPI報告タブ構造（週次時系列 + 右側ダッシュボード + CTA別詳細）を再現
# 既存の「ST_KPI報告」タブは変更しない
#
# 構造:
#   行1: タイトル
#   行2: 週ヘッダー（3ヶ月分 × W1-W4・累積 = 15列）
#   行3: ▼友達獲得（LINE登録）セクション
#   行4: LINE登録CV
#   行5: 目標
#   行6: 目標比
#   行7: CPF（LINE登録CPA）
#   行8: COST
#   行9: IMP
#   行10: CTR
#   行11: CVR
#   行12: CPM
#   行13: （空行）
#   行14: ▼LINE応募セクション
#   行15: 応募CV
#   行16: 応募目標
#   行17: 目標比
#   行18: 応募CPA
#   行19: 転換率（LINE→応募）
#   行20-32: グラフ用スペース
#   行33: ■友達獲得（LINE登録）当月累積
#   行34: ヘッダー: CTA|LINE登録CV|COST|CPF|応募CV|転換率|応募CPA
#   行35-40: CTA別データ（5CTA+合計）
#   行41: （空行）
#   行42: ■LINE応募 当月累積
#   行43: ヘッダー: CTA|応募CV|応募CPA|転換率
#   行44-49: CTA別データ（5CTA+合計）
#   右側（列R-V): 当月ダッシュボード（行3-9）
#
# 必要: pip install google-api-python-client google-auth

import sys, io
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE  = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
SPREADSHEET_ID = '1xXeCl4Xbkxz-w_jT49TmA3-voruL2cTbF1f308hZ5vQ'
TAB_NAME = 'ST_KPI報告_v2'

# ===== 月ラベル生成（当月・前月・前前月）=====

def subtract_months(y, m, delta):
    m -= delta
    while m <= 0:
        m += 12
        y -= 1
    return y, m

today = date.today()
months_ym = [
    subtract_months(today.year, today.month, 2),
    subtract_months(today.year, today.month, 1),
    (today.year, today.month),
]
month_labels = [f"{m}月" for _, m in months_ym]

week_headers = []
for ml in month_labels:
    week_headers += [f"{ml}W1", f"{ml}W2", f"{ml}W3", f"{ml}W4", f"{ml}累積"]

# ===== 認証 =====

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

service = build('sheets', 'v4', credentials=creds)

# ===== 既存タブ確認 =====

ss_meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
for s in ss_meta['sheets']:
    if s['properties']['title'] == TAB_NAME:
        print(f"「{TAB_NAME}」タブは既に存在します。")
        print("削除してから再実行するか、スクリプト冒頭の TAB_NAME を変更してください。")
        sys.exit(1)

# ===== タブ追加 =====

result = service.spreadsheets().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
    body={'requests': [{'addSheet': {'properties': {
        'title': TAB_NAME,
        'gridProperties': {
            'rowCount': 60,
            'columnCount': 23,
            'frozenRowCount': 2,
            'frozenColumnCount': 1,
        },
    }}}]}
).execute()
SHEET_ID = result['replies'][0]['addSheet']['properties']['sheetId']
print(f"タブ追加: {TAB_NAME} (sheetId={SHEET_ID})")

# ===== データ構築 =====

CTAS    = ['ペルソナLP', '塾ブランド診断', '気軽に診断', '新1年生', 'SNS ORG', '合計']
BLANK15 = [''] * 15

# 左側：週次時系列（行1-32）
main_values = [
    # 行1: タイトル
    [f'ST Meta広告 KPI報告 v2　（{month_labels[0]}〜{month_labels[2]}）'],
    # 行2: 週次ヘッダー
    ['KPI指標'] + week_headers,
    # 行3: ▼友達獲得セクション（セクションヘッダー）
    ['▼ 友達獲得（LINE登録）'],
    # 行4: LINE登録CV
    ['LINE登録CV'] + BLANK15,
    # 行5: 目標
    ['目標'] + BLANK15,
    # 行6: 目標比
    ['目標比'] + BLANK15,
    # 行7: CPF（LINE登録CPA）
    ['CPF（LINE登録CPA）'] + BLANK15,
    # 行8: COST
    ['COST'] + BLANK15,
    # 行9: IMP
    ['IMP'] + BLANK15,
    # 行10: CTR
    ['CTR'] + BLANK15,
    # 行11: CVR
    ['CVR'] + BLANK15,
    # 行12: CPM
    ['CPM'] + BLANK15,
    # 行13: 空行
    [],
    # 行14: ▼LINE応募セクション（セクションヘッダー）
    ['▼ LINE応募'],
    # 行15: 応募CV
    ['応募CV'] + BLANK15,
    # 行16: 応募目標
    ['応募目標'] + BLANK15,
    # 行17: 目標比
    ['目標比'] + BLANK15,
    # 行18: 応募CPA
    ['応募CPA'] + BLANK15,
    # 行19: 転換率（LINE→応募）
    ['転換率（LINE→応募）'] + BLANK15,
    # 行20-32: グラフ用スペース（13行）
    *[[] for _ in range(13)],
    # 行33: ■友達獲得 CTA テーブル セクションヘッダー
    ['■ 友達獲得（LINE登録）当月累積'],
    # 行34: CTA テーブル1 ヘッダー
    ['CTA', 'LINE登録CV', 'COST', 'CPF', '応募CV', '転換率', '応募CPA'],
    # 行35-40: CTA別データ
    *[[cta, '', '', '', '', '', ''] for cta in CTAS],
    # 行41: 空行
    [],
    # 行42: ■LINE応募 CTA テーブル セクションヘッダー
    ['■ LINE応募 当月累積'],
    # 行43: CTA テーブル2 ヘッダー
    ['CTA', '応募CV', '応募CPA', '転換率'],
    # 行44-49: CTA別データ
    *[[cta, '', '', ''] for cta in CTAS],
]

# 右側：当月ダッシュボード（列R-V = 0-based index 17-21）
# 行3から配置
dashboard_values = [
    ['当月ダッシュボード', '', '', '', ''],                         # R3
    ['指標', '実績', '目標/予算', '着地見込み', 'ビハインド/超過'], # R4
    ['COST', '', '', '', ''],                                       # R5
    ['LINE登録CV', '', '', '', ''],                                 # R6
    ['応募CV', '', '', '', ''],                                     # R7
    ['応募CPA', '', '', '', ''],                                    # R8
    ['CPF', '', '', '', ''],                                        # R9
]

# ===== データ書き込み =====

service.spreadsheets().values().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
    body={
        'valueInputOption': 'USER_ENTERED',
        'data': [
            {'range': f"'{TAB_NAME}'!A1", 'values': main_values},
            {'range': f"'{TAB_NAME}'!R3", 'values': dashboard_values},
        ],
    }
).execute()
print(f"データ書き込み完了 ({len(main_values)} 行)")

# ===== 書式設定 =====

BLUE_DARK  = {'red': 0.20, 'green': 0.47, 'blue': 0.75}
BLUE_MID   = {'red': 0.27, 'green': 0.51, 'blue': 0.71}
GREEN_MID  = {'red': 0.27, 'green': 0.57, 'blue': 0.36}
GRAY_LIGHT = {'red': 0.90, 'green': 0.90, 'blue': 0.90}
WHITE      = {'red': 1.00, 'green': 1.00, 'blue': 1.00}

def r(row_1indexed):
    """1-indexed row → 0-indexed for API"""
    return row_1indexed - 1

def section_bg(sheet_id, r0, r1, bg):
    return {
        'repeatCell': {
            'range': {'sheetId': sheet_id, 'startRowIndex': r0, 'endRowIndex': r1},
            'cell': {'userEnteredFormat': {
                'backgroundColor': bg,
                'textFormat': {'foregroundColor': WHITE, 'bold': True},
            }},
            'fields': 'userEnteredFormat(backgroundColor,textFormat)',
        }
    }

def label_bold(sheet_id, r0, r1):
    return {
        'repeatCell': {
            'range': {'sheetId': sheet_id, 'startRowIndex': r0, 'endRowIndex': r1,
                      'startColumnIndex': 0, 'endColumnIndex': 1},
            'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
            'fields': 'userEnteredFormat.textFormat.bold',
        }
    }

def header_row(sheet_id, r0, r1):
    return {
        'repeatCell': {
            'range': {'sheetId': sheet_id, 'startRowIndex': r0, 'endRowIndex': r1},
            'cell': {'userEnteredFormat': {
                'backgroundColor': GRAY_LIGHT,
                'textFormat': {'bold': True},
                'horizontalAlignment': 'CENTER',
            }},
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)',
        }
    }

def col_width(sheet_id, ci0, ci1, px):
    return {
        'updateDimensionProperties': {
            'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS',
                      'startIndex': ci0, 'endIndex': ci1},
            'properties': {'pixelSize': px},
            'fields': 'pixelSize',
        }
    }

requests = [
    # 行1: タイトル（紺背景・白太字）
    section_bg(SHEET_ID, r(1), r(2), BLUE_DARK),

    # 行2: 週ヘッダー（グレー背景・太字・中央）
    header_row(SHEET_ID, r(2), r(3)),

    # 行3: ▼友達獲得セクション（青背景）
    section_bg(SHEET_ID, r(3), r(4), BLUE_MID),

    # 行4-12: A列 ラベル太字
    label_bold(SHEET_ID, r(4), r(13)),

    # 行14: ▼LINE応募セクション（緑背景）
    section_bg(SHEET_ID, r(14), r(15), GREEN_MID),

    # 行15-19: A列 ラベル太字
    label_bold(SHEET_ID, r(15), r(20)),

    # 月境界線（5列ごとに縦線: 列F/K の右）
    {
        'updateBorders': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': r(2), 'endRowIndex': r(20),
                      'startColumnIndex': 5, 'endColumnIndex': 6},
            'right': {'style': 'SOLID_MEDIUM', 'color': BLUE_DARK},
        }
    },
    {
        'updateBorders': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': r(2), 'endRowIndex': r(20),
                      'startColumnIndex': 10, 'endColumnIndex': 11},
            'right': {'style': 'SOLID_MEDIUM', 'color': BLUE_DARK},
        }
    },

    # 行33: ■友達獲得CTAセクション（青背景）
    section_bg(SHEET_ID, r(33), r(34), BLUE_MID),

    # 行34: CTAテーブル1ヘッダー
    header_row(SHEET_ID, r(34), r(35)),

    # 行40: 合計行（グレー背景・太字）
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': r(40), 'endRowIndex': r(41)},
            'cell': {'userEnteredFormat': {
                'backgroundColor': GRAY_LIGHT,
                'textFormat': {'bold': True},
            }},
            'fields': 'userEnteredFormat(backgroundColor,textFormat)',
        }
    },

    # 行42: ■LINE応募CTAセクション（緑背景）
    section_bg(SHEET_ID, r(42), r(43), GREEN_MID),

    # 行43: CTAテーブル2ヘッダー
    header_row(SHEET_ID, r(43), r(44)),

    # 行49: 合計行
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': r(49), 'endRowIndex': r(50)},
            'cell': {'userEnteredFormat': {
                'backgroundColor': GRAY_LIGHT,
                'textFormat': {'bold': True},
            }},
            'fields': 'userEnteredFormat(backgroundColor,textFormat)',
        }
    },

    # ダッシュボード R3: ヘッダー（紺背景）
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': r(3), 'endRowIndex': r(4),
                      'startColumnIndex': 17, 'endColumnIndex': 22},
            'cell': {'userEnteredFormat': {
                'backgroundColor': BLUE_DARK,
                'textFormat': {'foregroundColor': WHITE, 'bold': True},
            }},
            'fields': 'userEnteredFormat(backgroundColor,textFormat)',
        }
    },

    # ダッシュボード R4: サブヘッダー（グレー背景）
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': r(4), 'endRowIndex': r(5),
                      'startColumnIndex': 17, 'endColumnIndex': 22},
            'cell': {'userEnteredFormat': {
                'backgroundColor': GRAY_LIGHT,
                'textFormat': {'bold': True},
                'horizontalAlignment': 'CENTER',
            }},
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)',
        }
    },

    # ダッシュボード R列（指標名）太字
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': r(5), 'endRowIndex': r(10),
                      'startColumnIndex': 17, 'endColumnIndex': 18},
            'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
            'fields': 'userEnteredFormat.textFormat.bold',
        }
    },

    # 列幅
    col_width(SHEET_ID, 0,   1,  160),   # A列（ラベル）
    col_width(SHEET_ID, 1,  16,   85),   # B-P列（週データ）
    col_width(SHEET_ID, 16, 17,   20),   # Q列（区切り）
    col_width(SHEET_ID, 17, 18,  130),   # R列（ダッシュボード指標名）
    col_width(SHEET_ID, 18, 22,  110),   # S-V列（ダッシュボード数値）
]

# ===== チャート追加 =====
# LINE登録CV（行4）・応募CV（行15）・応募CPA（行18）の折れ線グラフ（行20以降に配置）

def series(sheet_id, row_1indexed):
    return {'series': {'sourceRange': {'sources': [{
        'sheetId': sheet_id,
        'startRowIndex': r(row_1indexed), 'endRowIndex': r(row_1indexed) + 1,
        'startColumnIndex': 1, 'endColumnIndex': 16,
    }]}}}

requests.append({
    'addChart': {
        'chart': {
            'spec': {
                'title': '週別KPI推移',
                'basicChart': {
                    'chartType': 'LINE',
                    'legendPosition': 'BOTTOM_LEGEND',
                    'axis': [
                        {'position': 'BOTTOM_AXIS', 'title': '週'},
                        {'position': 'LEFT_AXIS',   'title': '件数（CV）'},
                        {'position': 'RIGHT_AXIS',  'title': '応募CPA（円）'},
                    ],
                    'domains': [{'domain': {'sourceRange': {'sources': [{
                        'sheetId': SHEET_ID,
                        'startRowIndex': r(2), 'endRowIndex': r(3),
                        'startColumnIndex': 1, 'endColumnIndex': 16,
                    }]}}}],
                    'series': [
                        {**series(SHEET_ID, 4),  'targetAxis': 'LEFT_AXIS'},   # LINE登録CV
                        {**series(SHEET_ID, 15), 'targetAxis': 'LEFT_AXIS'},   # 応募CV
                        {**series(SHEET_ID, 18), 'targetAxis': 'RIGHT_AXIS'},  # 応募CPA
                    ],
                    'headerCount': 0,
                }
            },
            'position': {
                'overlayPosition': {
                    'anchorCell': {'sheetId': SHEET_ID, 'rowIndex': r(20), 'columnIndex': 0},
                    'widthPixels': 820,
                    'heightPixels': 360,
                }
            }
        }
    }
})

service.spreadsheets().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
    body={'requests': requests}
).execute()
print("書式設定・チャート追加完了")

print()
print("=" * 60)
print(f"ST_KPI報告_v2 タブ作成完了")
print(f"URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={SHEET_ID}")
print(f"sheetId（kpi_report_st.py --v2 で必要）: {SHEET_ID}")
print("=" * 60)
print()
print("次のステップ:")
print("1. 上記URLでシート構造を確認")
print("2. python3 scripts/kpi_report_st.py 2026/05/19-2026/05/25 --write --v2")
