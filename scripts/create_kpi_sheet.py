# ST KPI報告用スプレッドシートを新規作成するスクリプト
# 必要: pip install google-api-python-client google-auth
#
# 構造（1タブ: ST_KPI報告）:
#   行1    : タイトル
#   行2    : 週次ヘッダー（3ヶ月分 × W1-W4・累積 = 15列）
#   行3-6  : データ行（LINE登録CV / 応募CV / 応募CPA / COST）
#   行7-22 : チャート用スペース（折れ線グラフが重なって配置される）
#   行23   : ■ 友達獲得（LINE登録）セクション
#   行24   : ヘッダー（CTA | LINE登録CV | COST | 応募CPA | CVR）
#   行25-30: CTA別データ行
#   行32   : ■ LINE応募セクション
#   行33   : ヘッダー（CTA | 応募CV | 応募CPA | CVR）
#   行34-39: CTA別データ行

import sys, io
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

# ========== 月ラベル生成（当月・前月・前前月）==========

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

# 列ヘッダー: 前前月W1〜当月累積 (15列)
week_headers = []
for ml in month_labels:
    week_headers += [f"{ml}W1", f"{ml}W2", f"{ml}W3", f"{ml}W4", f"{ml}累積"]

# ========== 認証 ==========

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

service = build('sheets', 'v4', credentials=creds)

# ========== スプレッドシート新規作成 ==========

spreadsheet_body = {
    'properties': {
        'title': 'ST Meta広告 KPI報告',
        'locale': 'ja_JP',
        'timeZone': 'Asia/Tokyo',
    },
    'sheets': [{
        'properties': {
            'title': 'ST_KPI報告',
            'gridProperties': {
                'rowCount': 100,
                'columnCount': 20,
                'frozenRowCount': 2,
                'frozenColumnCount': 1,
            }
        }
    }]
}

ss = service.spreadsheets().create(body=spreadsheet_body).execute()
SPREADSHEET_ID = ss['spreadsheetId']
SHEET_ID = ss['sheets'][0]['properties']['sheetId']
print(f"スプレッドシート作成: {SPREADSHEET_ID}")

# ========== データ書き込み ==========

CTAS = ['全体', 'ペルソナLP', '塾ブランド診断', '気軽に診断', '新1年生', 'SNS ORG']

values = [
    # Row 1: タイトル
    [f'ST Meta広告 KPI報告　（{month_labels[0]}〜{month_labels[2]}）'],

    # Row 2: 週次ヘッダー
    ['KPI指標'] + week_headers,

    # Row 3-6: データ行（kpi-reportスキルがここに書き込む）
    ['LINE登録CV'] + ['']*15,
    ['応募CV']     + ['']*15,
    ['応募CPA']    + ['']*15,
    ['COST']       + ['']*15,

    # Row 7-22: チャート用スペース（空行）
    *[[] for _ in range(16)],

    # Row 23: 友達獲得セクションタイトル
    ['■ 友達獲得（LINE登録）　当月累積'],

    # Row 24: ヘッダー
    ['CTA', 'LINE登録CV', 'COST', '応募CPA', 'CVR'],

    # Row 25-30: CTA別データ
    *[[cta, '', '', '', ''] for cta in CTAS],

    # Row 31: 空行
    [],

    # Row 32: LINE応募セクションタイトル
    ['■ LINE応募　当月累積'],

    # Row 33: ヘッダー
    ['CTA', '応募CV', '応募CPA', 'CVR'],

    # Row 34-39: CTA別データ
    *[[cta, '', '', ''] for cta in CTAS],
]

service.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range="'ST_KPI報告'!A1",
    valueInputOption='USER_ENTERED',
    body={'values': values}
).execute()
print("データ書き込み完了")

# ========== 書式設定・チャート追加 ==========

# 色定義
BLUE_DARK  = {'red': 0.20, 'green': 0.47, 'blue': 0.75}
BLUE_MID   = {'red': 0.27, 'green': 0.51, 'blue': 0.71}
GRAY_LIGHT = {'red': 0.90, 'green': 0.90, 'blue': 0.90}
WHITE      = {'red': 1.00, 'green': 1.00, 'blue': 1.00}

requests = [

    # ---------- タイトル行（行1）: 紺背景・白太字 ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 0, 'endRowIndex': 1},
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': BLUE_DARK,
                    'textFormat': {
                        'foregroundColor': WHITE,
                        'bold': True,
                        'fontSize': 13,
                    },
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
        }
    },

    # ---------- ヘッダー行（行2）: グレー背景・太字・中央揃え ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 1, 'endRowIndex': 2},
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': GRAY_LIGHT,
                    'textFormat': {'bold': True},
                    'horizontalAlignment': 'CENTER',
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
        }
    },

    # ---------- データ行 A列（KPI指標ラベル）: 太字 ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 2, 'endRowIndex': 6, 'startColumnIndex': 0, 'endColumnIndex': 1},
            'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
            'fields': 'userEnteredFormat.textFormat.bold'
        }
    },

    # ---------- データ行 数値列: 右揃え ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 2, 'endRowIndex': 6, 'startColumnIndex': 1, 'endColumnIndex': 16},
            'cell': {'userEnteredFormat': {'horizontalAlignment': 'RIGHT'}},
            'fields': 'userEnteredFormat.horizontalAlignment'
        }
    },

    # ---------- 月境界線（5列ごとに縦線）: 前前月/前月/当月の区切り ----------
    # 6列目（累積後）の右罫線
    {
        'updateBorders': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 1, 'endRowIndex': 6, 'startColumnIndex': 5, 'endColumnIndex': 6},
            'right': {'style': 'SOLID_MEDIUM', 'color': BLUE_DARK}
        }
    },
    {
        'updateBorders': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 1, 'endRowIndex': 6, 'startColumnIndex': 10, 'endColumnIndex': 11},
            'right': {'style': 'SOLID_MEDIUM', 'color': BLUE_DARK}
        }
    },

    # ---------- 友達獲得セクションタイトル（行23）: 青背景・白太字 ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 22, 'endRowIndex': 23},
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': BLUE_MID,
                    'textFormat': {'foregroundColor': WHITE, 'bold': True},
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
        }
    },

    # ---------- 友達獲得ヘッダー（行24）: グレー背景・太字・中央揃え ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 23, 'endRowIndex': 24},
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': GRAY_LIGHT,
                    'textFormat': {'bold': True},
                    'horizontalAlignment': 'CENTER',
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
        }
    },

    # ---------- LINE応募セクションタイトル（行32）: 青背景・白太字 ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 31, 'endRowIndex': 32},
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': BLUE_MID,
                    'textFormat': {'foregroundColor': WHITE, 'bold': True},
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
        }
    },

    # ---------- LINE応募ヘッダー（行33）: グレー背景・太字・中央揃え ----------
    {
        'repeatCell': {
            'range': {'sheetId': SHEET_ID, 'startRowIndex': 32, 'endRowIndex': 33},
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': GRAY_LIGHT,
                    'textFormat': {'bold': True},
                    'horizontalAlignment': 'CENTER',
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
        }
    },

    # ---------- 列幅 ----------
    # A列（KPI指標 / CTA名）
    {
        'updateDimensionProperties': {
            'range': {'sheetId': SHEET_ID, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1},
            'properties': {'pixelSize': 140},
            'fields': 'pixelSize'
        }
    },
    # データ列 B〜P（15列）
    {
        'updateDimensionProperties': {
            'range': {'sheetId': SHEET_ID, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 16},
            'properties': {'pixelSize': 85},
            'fields': 'pixelSize'
        }
    },

    # ---------- チャート追加（行7 以降にオーバーレイ）----------
    # LINE登録CV（左軸）/ 応募CV（左軸）/ 応募CPA（右軸）の折れ線グラフ
    {
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
                        'domains': [{
                            'domain': {
                                'sourceRange': {
                                    'sources': [{
                                        'sheetId':         SHEET_ID,
                                        'startRowIndex':   1,   # 行2（ヘッダー）
                                        'endRowIndex':     2,
                                        'startColumnIndex': 1,  # 列B
                                        'endColumnIndex':  16,  # 列P+1
                                    }]
                                }
                            }
                        }],
                        'series': [
                            # LINE登録CV（行3）
                            {
                                'series': {
                                    'sourceRange': {
                                        'sources': [{
                                            'sheetId':         SHEET_ID,
                                            'startRowIndex':   2,
                                            'endRowIndex':     3,
                                            'startColumnIndex': 1,
                                            'endColumnIndex':  16,
                                        }]
                                    }
                                },
                                'targetAxis': 'LEFT_AXIS',
                            },
                            # 応募CV（行4）
                            {
                                'series': {
                                    'sourceRange': {
                                        'sources': [{
                                            'sheetId':         SHEET_ID,
                                            'startRowIndex':   3,
                                            'endRowIndex':     4,
                                            'startColumnIndex': 1,
                                            'endColumnIndex':  16,
                                        }]
                                    }
                                },
                                'targetAxis': 'LEFT_AXIS',
                            },
                            # 応募CPA（行5）→ 右軸
                            {
                                'series': {
                                    'sourceRange': {
                                        'sources': [{
                                            'sheetId':         SHEET_ID,
                                            'startRowIndex':   4,
                                            'endRowIndex':     5,
                                            'startColumnIndex': 1,
                                            'endColumnIndex':  16,
                                        }]
                                    }
                                },
                                'targetAxis': 'RIGHT_AXIS',
                            },
                        ],
                        'headerCount': 0,
                    }
                },
                'position': {
                    'overlayPosition': {
                        'anchorCell': {
                            'sheetId':    SHEET_ID,
                            'rowIndex':   6,   # 行7（0-indexed=6）
                            'columnIndex': 0,
                        },
                        'widthPixels':  820,
                        'heightPixels': 360,
                    }
                }
            }
        }
    },
]

service.spreadsheets().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
    body={'requests': requests}
).execute()
print("書式設定・チャート追加完了")

# ========== 完了メッセージ ==========
print()
print("=" * 60)
print("新規スプレッドシート作成完了")
print(f"URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
print(f"SPREADSHEET_ID: {SPREADSHEET_ID}")
print("=" * 60)
print()
print("次のステップ:")
print("1. 上記URLを開いてレイアウトを確認する")
print("2. SPREADSHEET_IDをkpi-report SKILL.md STEP 5に追記する")
