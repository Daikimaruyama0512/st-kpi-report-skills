"""
STチームのMeta広告担当3名分のMBO草案をGoogleスプレッドシートに作成する。
フォーマット: 丸山　案２ (1YUqibxSwN0r8JE8sjV7UmotfzQEDksQ6VAblfTKBDrY)
"""
# 必要: pip install google-api-python-client google-auth-oauthlib

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN_FILE = "/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

# ---- 認証 ----
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('sheets', 'v4', credentials=creds)


# ---- MBOデータ定義 ----
# 列インデックス (0-based): A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8, J=9, K=10, L=11, M=12, N=13, O=14, P=15
# 月の割り当て: C-D=4月, E-F=5月, G-H=6月, I-J=7月, K-L=8月, M-N=9月, O-P=FY26上期

MONTH_COLS = {
    '4月': (2, 3),   # C, D
    '5月': (4, 5),   # E, F
    '6月': (6, 7),
    '7月': (8, 9),
    '8月': (10, 11),
    '9月': (12, 13),
    'FY26': (14, 15),
}

# ---- 空の行を16列で生成するヘルパー ----
def empty_row(n=16):
    return [''] * n

# ---- 月ヘッダーを16列で生成 ----
def month_header_row():
    row = empty_row()
    for month, (c, _) in MONTH_COLS.items():
        if month == 'FY26':
            row[c] = 'FY26 上期振り返り'
        else:
            row[c] = f'{month}振り返り'
    return row

# ---- 目標/実績/目標比の行を生成 ----
def make_label_row(label, fy26_value=None):
    row = empty_row()
    for month, (c, _) in MONTH_COLS.items():
        row[c] = label
    if fy26_value:
        row[MONTH_COLS['FY26'][1]] = fy26_value
    return row

# ---- KEEP/PROBLEM/TRYラベル行 ----
def make_kpt_row(kpt_label):
    row = empty_row()
    for month, (c, _) in MONTH_COLS.items():
        row[c] = kpt_label
    return row

# ---- 4月テーマ（共通） ----
APR_THEME = 'テーマ：ユーザーの悩みに合わせたLPや着地点の設計'
APR_WHY_WHAT_HOW = (
    'WHY：CVにつながるLine登録の数を増やすため、ターゲティング精度の向上により、CVRを向上させることができるため\n'
    'WHAT：遷移先のLINEの画面の訴求内容と広告での訴求内容に一貫性を持たせる\n'
    'HOW：LINE登録の担当に働きかけることでカスタマージャーニーの中での一貫性を担保する'
)

# ---- 定性目標（4月・共通） ----
APR_QUALITATIVE = (
    'WHAT：Lineの表示画面と広告の内容に一貫性を持たせる（訴求軸を揃える）\n'
    'WHY：内容の乖離による離脱を防ぎ、また取りきれていない潜在層を取りに行くため\n'
    'HOW：月一で魚住さんとのmtgを設定'
)

# ---- 3名分の個人設定 ----
PERSONS = [
    {
        'name': '阪西　草案',
        'may_theme': 'テーマ：CPAの安定化と高パフォーマンスクリエイティブの横展開',
        'may_why_what_how': (
            'WHY：FY25後半のCPA変動を踏まえ、再現性ある運用基盤を構築するため\n'
            'WHAT：上位CPAクリエイティブのA/Bテスト拡張と消耗サイクルの可視化\n'
            'HOW：週次でcreative評価MTGを実施、BigQueryダッシュボードを活用して効果検証'
        ),
        'qualitative': (
            'WHAT：新規クリエイティブの制作フローを確立し、毎月3本以上テスト実施\n'
            'WHY：広告の消耗が激しいため、常にフレッシュなクリエイティブを供給する体制が必要\n'
            'HOW：制作チームとの週次定例設定、クリエイティブブリーフテンプレートの整備'
        ),
    },
    {
        'name': '丸山　草案',
        'may_theme': 'テーマ：訴求軸の体系化とシナリオドリブン広告運用',
        'may_why_what_how': (
            'WHY：広告シナリオとCVRの相関を明確にし、次の施策に活かすため\n'
            'WHAT：STシナリオ別CPAの可視化、PASONA法則に基づく新規クリエイティブ5本制作\n'
            'HOW：BigQueryのシナリオビューを活用した月次分析レポートの作成・共有'
        ),
        'qualitative': (
            'WHAT：BigQueryを活用したシナリオ分析レポートを月次で作成・共有\n'
            'WHY：データに基づく意思決定でチーム全体の運用精度を向上させるため\n'
            'HOW：毎月15日までにレポート提出、Slackでの共有と議論の場を設ける'
        ),
    },
    {
        'name': '原　草案',
        'may_theme': 'テーマ：Meta広告運用の基礎習得とファーストCV獲得',
        'may_why_what_how': (
            'WHY：運用の全体像を早期に把握し、チームへの貢献を開始するため\n'
            'WHAT：既存広告の命名規則・CPAの読み方習得、担当広告セット1本の管理開始\n'
            'HOW：先輩メンバーとのOJT週2回実施、knowledge/meta-ads-naming.mdの通読'
        ),
        'qualitative': (
            'WHAT：Meta広告の基本KPI（CPA/CVR/CPM）を正確に読み取り、週次レポートを作成\n'
            'WHY：基礎力の定着がスピーディな独り立ちにつながるため\n'
            'HOW：毎週金曜にメンターチェック、KPI読み解きの練習問題を週3問解く'
        ),
    },
]


def build_sheet_data(person):
    """各メンバーのシートデータ（47行 × 16列）を生成する"""

    def theme_row(apr_text, may_text):
        row = empty_row()
        row[0] = 'テーマ：'
        row[MONTH_COLS['4月'][0]] = apr_text
        row[MONTH_COLS['5月'][0]] = may_text
        # 6〜9月・FY26は空欄（ラベルのみ）
        for m in ['6月', '7月', '8月', '9月', 'FY26']:
            row[MONTH_COLS[m][0]] = 'テーマ：'
        return row

    def why_row(apr_text, may_text):
        row = empty_row()
        row[0] = 'WHY：なぜこのテーマを選んだか\n┗KPI達成に寄与するか\nWHAT：なにを作るのか\n┗成果物は何か        \nHOW：どのような手順で作るのか\n┗プロセスは何か'
        row[MONTH_COLS['4月'][0]] = apr_text
        row[MONTH_COLS['5月'][0]] = may_text
        for m in ['6月', '7月', '8月', '9月', 'FY26']:
            row[MONTH_COLS[m][0]] = 'WHY：\nWHAT：\nHOW：'
        return row

    def quantitative_row():
        row = empty_row()
        row[0] = '◆定量目標'
        for month, (c, d) in MONTH_COLS.items():
            row[c] = '◆自己評価'
            row[d] = '◆上長評価'
        row[MONTH_COLS['FY26'][0]] = '◆定量目標'
        return row

    def qualitative_row():
        row = empty_row()
        row[0] = '◆定性目標'
        for month, (c, _) in MONTH_COLS.items():
            row[c] = '◆KEEP'
        return row

    def problem_row():
        row = empty_row()
        for month, (c, _) in MONTH_COLS.items():
            row[c] = '◆PROBLEM'
        return row

    def try_row():
        row = empty_row()
        for month, (c, _) in MONTH_COLS.items():
            row[c] = '◆TRY'
        return row

    def keep_row():
        row = empty_row()
        for month, (c, _) in MONTH_COLS.items():
            row[c] = '◆KEEP'
        return row

    # 行1: タイトル
    r1 = empty_row()
    r1[0] = f"{person['name']}　FY26上期 Meta広告 MBO（2026年4月〜9月）"

    # 行2: 月ヘッダー
    r2 = month_header_row()

    # 行3: チーム目標
    r3 = empty_row()
    r3[0] = 'チーム目標'

    # 行4: 目標 (FY26上期: 面談249件・採用1278件)
    r4 = make_label_row('目標')
    r4[MONTH_COLS['FY26'][0]] = '目標（面談）'
    r4[MONTH_COLS['FY26'][1]] = '249'

    # 行5: 実績
    r5 = make_label_row('実績')

    # 行6: 目標比
    r6 = make_label_row('目標比')
    r6[MONTH_COLS['FY26'][0]] = '目標（採用）'
    r6[MONTH_COLS['FY26'][1]] = '1278'

    # 行7: 個人目標
    r7 = empty_row()
    r7[0] = '個人目標（媒体ごと）'

    # 行8-16: Meta広告ブロック1
    r8 = empty_row()
    r8[0] = 'Meta広告'
    for m, (c, _) in MONTH_COLS.items():
        r8[c] = '目標'
    r9 = make_label_row('実績')
    r9[0] = ''
    r10 = make_label_row('目標比')
    r10[0] = ''
    r11 = make_kpt_row('◆KEEP')
    r11[0] = ''
    r12 = empty_row()  # KEEP内容
    r13 = make_kpt_row('◆PROBLEM')
    r13[0] = ''
    r14 = empty_row()  # PROBLEM内容
    r15 = make_kpt_row('◆TRY')
    r15[0] = ''
    r16 = empty_row()  # TRY内容

    # 行17-25: Meta広告ブロック2（同構造）
    r17 = empty_row()
    r17[0] = 'Meta広告'
    for m, (c, _) in MONTH_COLS.items():
        r17[c] = '目標'
    r18 = make_label_row('実績')
    r18[0] = ''
    r19 = make_label_row('目標比')
    r19[0] = ''
    r20 = make_kpt_row('◆KEEP')
    r20[0] = ''
    r21 = empty_row()
    r22 = make_kpt_row('◆PROBLEM')
    r22[0] = ''
    r23 = empty_row()
    r24 = make_kpt_row('◆TRY')
    r24[0] = ''
    r25 = empty_row()

    # 行26: テーマ1
    r26 = theme_row(APR_THEME, person['may_theme'])

    # 行27: WHY/WHAT/HOW
    r27 = why_row(APR_WHY_WHAT_HOW, person['may_why_what_how'])

    # 行28: 定量目標
    r28 = quantitative_row()

    # 行29: 半期目標説明
    r29 = empty_row()
    r29[0] = '半期目標を個人で設定'

    # 行30: 定性目標 / KEEP
    r30 = qualitative_row()

    # 行31: 定性目標のWHAT/WHY/HOW
    r31 = empty_row()
    r31[0] = person['qualitative']

    # 行32: PROBLEM
    r32 = problem_row()
    r32[0] = ''

    # 行33: 空
    r33 = empty_row()

    # 行34: TRY
    r34 = try_row()
    r34[0] = ''

    # 行35: 空
    r35 = empty_row()

    # 行36-45: 第2テーマブロック（全月空欄テンプレート）
    r36 = theme_row('テーマ：', 'テーマ：')
    r36[MONTH_COLS['4月'][0]] = 'テーマ：'

    r37 = empty_row()
    r37[0] = 'WHY：なぜこのテーマを選んだか\n┗KPI達成に寄与するか\nWHAT：なにを作るのか\n┗成果物は何か        \nHOW：どのような手順で作るのか\n┗プロセスは何か'
    for m, (c, _) in MONTH_COLS.items():
        r37[c] = 'WHY：\nWHAT：\nHOW：'

    r38 = quantitative_row()

    r39 = empty_row()
    r39[0] = '半期目標を個人で設定\n例）アウトプットの数\n例）業務時間・工数'

    r40 = qualitative_row()

    r41 = empty_row()
    r41[0] = 'WHAT：\nWHY：\nHOW：'

    r42 = problem_row()
    r42[0] = ''

    r43 = empty_row()

    r44 = try_row()
    r44[0] = ''

    r45 = empty_row()

    # 行46: MBO関連なんでも
    r46 = empty_row()
    for m, (c, _) in MONTH_COLS.items():
        r46[c] = 'MBO関連なんでも'

    # 行47: 自由記述
    r47 = empty_row()
    r47[0] = ('MBOに関連する提案・相談・感想など、自由に記載してください。\n'
              '例）\n'
              '・他の人のMBOが何かわからないので、共有機会欲しい\n'
              '・振り返りMTGのアジェンダはこういう風にしたらよいのでは？\n'
              '・テーマを具体化するときの[WHY/WHAT/HOW]の書き方に困っている\n'
              '・月中にテーマよりも重要度,関心の高いテーマが出てきてしまう')

    return [
        r1, r2, r3, r4, r5, r6, r7,
        r8, r9, r10, r11, r12, r13, r14, r15, r16,
        r17, r18, r19, r20, r21, r22, r23, r24, r25,
        r26, r27, r28, r29, r30, r31, r32, r33, r34, r35,
        r36, r37, r38, r39, r40, r41, r42, r43, r44, r45,
        r46, r47,
    ]


# ---- スプレッドシート新規作成 ----
sheet_names = [p['name'] for p in PERSONS]

body = {
    "properties": {"title": "【ST Meta広告】FY26上期 MBO草案（阪西・丸山・原）"},
    "sheets": [
        {"properties": {"title": name, "gridProperties": {"rowCount": 60, "columnCount": 16}}}
        for name in sheet_names
    ]
}

print("スプレッドシートを作成中...")
ss = service.spreadsheets().create(body=body).execute()
ssid = ss['spreadsheetId']
print(f"作成完了: https://docs.google.com/spreadsheets/d/{ssid}")

# シートID取得
sheet_id_map = {}
for s in ss['sheets']:
    sheet_id_map[s['properties']['title']] = s['properties']['sheetId']

# ---- データ書き込み ----
batch_data = []
for person in PERSONS:
    rows = build_sheet_data(person)
    sheet_name = person['name']
    batch_data.append({
        "range": f"'{sheet_name}'!A1",
        "values": rows
    })

print("データを書き込み中...")
service.spreadsheets().values().batchUpdate(
    spreadsheetId=ssid,
    body={"valueInputOption": "USER_ENTERED", "data": batch_data}
).execute()
print("データ書き込み完了")

# ---- 書式設定 ----
def rgb(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return {"red": r, "green": g, "blue": b}

def make_format_request(sheet_id, start_row, end_row, bg_hex, bold=False, font_color_hex=None):
    """指定行範囲に背景色・太字を設定するリクエスト"""
    cell_format = {
        "backgroundColor": rgb(bg_hex),
        "wrapStrategy": "WRAP",
    }
    if bold:
        cell_format["textFormat"] = {"bold": True}
        if font_color_hex:
            cell_format["textFormat"]["foregroundColor"] = rgb(font_color_hex)
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": 0,
                "endColumnIndex": 16,
            },
            "cell": {"userEnteredFormat": cell_format},
            "fields": "userEnteredFormat(backgroundColor,wrapStrategy,textFormat)",
        }
    }

format_requests = []
for person in PERSONS:
    sid = sheet_id_map[person['name']]

    # 行1: タイトル（薄グレー）
    format_requests.append(make_format_request(sid, 0, 1, "F3F3F3", bold=True))

    # 行2: 月ヘッダー（青・白文字・太字）
    format_requests.append(make_format_request(sid, 1, 2, "4472C4", bold=True, font_color_hex="FFFFFF"))

    # 行3: チーム目標（薄緑）
    format_requests.append(make_format_request(sid, 2, 3, "D9EAD3", bold=True))

    # 行4-6: 目標/実績/目標比（薄緑系）
    format_requests.append(make_format_request(sid, 3, 6, "EAF4EA"))

    # 行7: 個人目標（オレンジ・太字）
    format_requests.append(make_format_request(sid, 6, 7, "FCE5CD", bold=True))

    # 行8-10: Meta広告ブロック1 目標行（薄オレンジ）
    format_requests.append(make_format_request(sid, 7, 10, "FFF2CC"))

    # 行11-16: KEEP/PROBLEM/TRYラベル（薄グレー）
    for row_idx in [10, 12, 14]:
        format_requests.append(make_format_request(sid, row_idx, row_idx + 1, "F3F3F3", bold=True))

    # 行17-25: Meta広告ブロック2（同様）
    format_requests.append(make_format_request(sid, 16, 19, "FFF2CC"))
    for row_idx in [19, 21, 23]:
        format_requests.append(make_format_request(sid, row_idx, row_idx + 1, "F3F3F3", bold=True))

    # 行26: テーマ1（青系・太字）
    format_requests.append(make_format_request(sid, 25, 26, "CFE2F3", bold=True))

    # 行27: WHY/WHAT/HOW（薄青）
    format_requests.append(make_format_request(sid, 26, 27, "E8F4FF"))

    # 行28: 定量目標（黄色・太字）
    format_requests.append(make_format_request(sid, 27, 28, "FFF2CC", bold=True))

    # 行30: 定性目標（ピンク・太字）
    format_requests.append(make_format_request(sid, 29, 30, "EAD1DC", bold=True))

    # 行36: テーマ2（青系・太字）
    format_requests.append(make_format_request(sid, 35, 36, "CFE2F3", bold=True))

    # 行37: WHY/WHAT/HOW（薄青）
    format_requests.append(make_format_request(sid, 36, 37, "E8F4FF"))

    # 行38: 定量目標（黄色・太字）
    format_requests.append(make_format_request(sid, 37, 38, "FFF2CC", bold=True))

    # 行40: 定性目標（ピンク・太字）
    format_requests.append(make_format_request(sid, 39, 40, "EAD1DC", bold=True))

    # 行46: MBO関連なんでも（薄グレー・太字）
    format_requests.append(make_format_request(sid, 45, 46, "F3F3F3", bold=True))

    # 列幅自動調整 (A〜P)
    format_requests.append({
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sid,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": 16,
            }
        }
    })

    # 行の高さを少し広めに (wrap対応)
    format_requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sid,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": 47,
            },
            "properties": {"pixelSize": 80},
            "fields": "pixelSize",
        }
    })

print("書式を適用中...")
service.spreadsheets().batchUpdate(
    spreadsheetId=ssid,
    body={"requests": format_requests}
).execute()
print("書式適用完了")

print(f"\n完成しました！")
print(f"URL: https://docs.google.com/spreadsheets/d/{ssid}")
print(f"シート: {', '.join(sheet_names)}")
