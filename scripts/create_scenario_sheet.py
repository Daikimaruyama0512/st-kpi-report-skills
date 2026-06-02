# STシナリオ管理スプレッドシートを新規作成するスクリプト
# 構成: 元データ（Meta成果相当）+ シナリオ管理（集計シート）
import sys, io, json, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token

def api_post(url, body):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

def values_batch_update(spreadsheet_id, data_list, value_input_option="USER_ENTERED"):
    """複数範囲の値を一括更新 (POST /values:batchUpdate)"""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"
    return api_post(url, {
        "valueInputOption": value_input_option,
        "data": data_list,
    })

def sheet_range(tab_name, cell_range):
    """タブ名+セル範囲 の文字列を生成（quotes付き）"""
    return f"'{tab_name}'!{cell_range}"

# ─────────────────────────────────────────
# 1. 新規スプレッドシート作成
# ─────────────────────────────────────────
print("1. 新規スプレッドシート作成中...")
create_res = api_post(
    "https://sheets.googleapis.com/v4/spreadsheets",
    {
        "properties": {"title": "STシナリオ管理"},
        "sheets": [
            {"properties": {"title": "元データ", "index": 0}},
            {"properties": {"title": "シナリオ管理", "index": 1}},
        ]
    }
)
SPREADSHEET_ID = create_res['spreadsheetId']
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
print(f"  作成完了: {SPREADSHEET_URL}")

sheet_ids = {}
for s in create_res['sheets']:
    sheet_ids[s['properties']['title']] = s['properties']['sheetId']

# ─────────────────────────────────────────
# 2. 値を一括設定（values:batchUpdate）
# ─────────────────────────────────────────
print("2. ヘッダー・数式を設定中...")

# 元データ: ヘッダー行
META_HEADERS = [
    "キャンペーン名",   # A
    "広告セット名",     # B
    "広告の名前",       # C
    "リーチ",           # D
    "インプレッション", # E
    "フリークエンシー", # F
    "消化金額(JPY)",    # G
    "リンクのクリック", # H
    "",                 # I （空列）
    "結果タイプ",       # J
    "",                 # K
    "",                 # L
    "",                 # M
    "結果(CV)",         # N
    "日付",             # O
]

# シナリオ管理: 行1〜3
ROW1 = ["期間", "", "", "＜参考＞", "", "目標CPA", "", "", "", "目標CVR", "目標CTR"]
ROW2 = ["", "2026/4/1", "", "STシナリオ管理", "", "¥2,500", "", "", "", "10%以上", "0.32%以上",
        "", "", "", "", "", "", "WHO", "", "WHAT", "", "", "", "", "HOW", "", "",
        "シナリオチェック", "", "", "元データ"]
ROW2_B2 = "2026/4/30"  # B2（集計終了日）は別行

ROW3 = [
    "担当者", "CP", "広告名", "CTA",
    "CV", "CPA", "COST", "IMP", "CT", "CVR", "CTR", "CPM",
    "稼働状況", "終了日", "停止理由/運用メモ", "メディアタイプ", "出稿日",
    "想定ターゲット", "変更内容", "訴求", "限定", "中身", "冒頭", "悩み",
    "シナリオ", "文字数", "Canvaリンク", "Gem", "修正", "JSON", "転記",
    "仮説・工夫した点", "振り返り", "横展開案", "作成ステータス", "入稿可否",
]

# シナリオ管理: データ行（10行分）
SCENARIO_ROWS = []
for r in range(10):
    row_num = r + 4
    b = row_num
    row = ["", "", "", ""]  # A〜D 手入力

    # E: CV
    row.append(f"=SUMIFS('元データ'!$N:$N,'元データ'!$A:$A,\"*\"&B{b}&\"*\",'元データ'!$C:$C,\"*\"&C{b}&\"*\",'元データ'!$O:$O,\">=\"&$B$1,'元データ'!$O:$O,\"<=\"&$B$2)")
    # F: CPA
    row.append(f"=IFERROR(G{b}/E{b},\"-\")")
    # G: COST
    row.append(f"=SUMIFS('元データ'!$G:$G,'元データ'!$A:$A,\"*\"&$B{b}&\"*\",'元データ'!$C:$C,\"*\"&C{b}&\"*\",'元データ'!$O:$O,\">=\"&$B$1,'元データ'!$O:$O,\"<=\"&$B$2)")
    # H: IMP
    row.append(f"=SUMIFS('元データ'!$E:$E,'元データ'!$A:$A,\"*\"&$B{b}&\"*\",'元データ'!$C:$C,\"*\"&C{b}&\"*\",'元データ'!$O:$O,\">=\"&$B$1,'元データ'!$O:$O,\"<=\"&$B$2)")
    # I: CT
    row.append(f"=SUMIFS('元データ'!$H:$H,'元データ'!$A:$A,\"*\"&$B{b}&\"*\",'元データ'!$C:$C,\"*\"&C{b}&\"*\",'元データ'!$O:$O,\">=\"&$B$1,'元データ'!$O:$O,\"<=\"&$B$2)")
    # J: CVR
    row.append(f"=IFERROR(E{b}/I{b},\"-\")")
    # K: CTR
    row.append(f"=IFERROR(I{b}/H{b},\"-\")")
    # L: CPM
    row.append(f"=IFERROR(G{b}/H{b}*1000,\"-\")")

    # M〜X: 手入力（12列）
    row += [""] * 12

    # Y: シナリオ本文（手入力）
    row.append("")

    # Z: 文字数
    row.append(f"=IF(Y{b}=\"\",\"\",LEN(Y{b}))")

    # AA〜AD: 手入力（4列）
    row += [""] * 4

    # AE: 転記チェック
    row.append(f"=IF(C{b}=\"\",\"\",IF(COUNTIF('元データ'!$C:$C,C{b})>0,\"済\",\"未\"))")

    # AF〜AJ: 手入力（5列）
    row += [""] * 5

    SCENARIO_ROWS.append(row)

values_batch_update(SPREADSHEET_ID, [
    {"range": sheet_range("元データ", "A1:O1"),   "values": [META_HEADERS]},
    {"range": sheet_range("シナリオ管理", "A1:AJ1"), "values": [ROW1]},
    {"range": sheet_range("シナリオ管理", "A2:AJ2"), "values": [ROW2]},
    {"range": sheet_range("シナリオ管理", "B2"),     "values": [["2026/4/30"]]},
    {"range": sheet_range("シナリオ管理", "A3:AJ3"), "values": [ROW3]},
    {"range": sheet_range("シナリオ管理", f"A4:AJ{4+len(SCENARIO_ROWS)-1}"), "values": SCENARIO_ROWS},
])

# ─────────────────────────────────────────
# 3. 書式設定（batchUpdate）
# ─────────────────────────────────────────
print("3. 書式設定中（ヘッダー太字・行固定・列幅）...")

scenario_sid = sheet_ids["シナリオ管理"]
meta_sid     = sheet_ids["元データ"]

def repeat_cell(sheet_id, r0, r1, c0, c1, fmt, fields):
    return {"repeatCell": {
        "range": {"sheetId": sheet_id, "startRowIndex": r0, "endRowIndex": r1,
                  "startColumnIndex": c0, "endColumnIndex": c1},
        "cell": {"userEnteredFormat": fmt},
        "fields": f"userEnteredFormat({fields})",
    }}

requests = [
    # シナリオ管理 行3 ヘッダー: 太字+青背景
    repeat_cell(scenario_sid, 2, 3, 0, 36,
        {"textFormat": {"bold": True},
         "backgroundColor": {"red": 0.63, "green": 0.79, "blue": 0.95}},
        "textFormat,backgroundColor"),

    # シナリオ管理 行1〜2: 薄黄背景
    repeat_cell(scenario_sid, 0, 2, 0, 36,
        {"backgroundColor": {"red": 1.0, "green": 0.98, "blue": 0.80}},
        "backgroundColor"),

    # シナリオ管理 数式列（E〜L = 4〜11）: 薄緑
    repeat_cell(scenario_sid, 3, 13, 4, 12,
        {"backgroundColor": {"red": 0.85, "green": 0.96, "blue": 0.85}},
        "backgroundColor"),

    # Z列（文字数 = 25）: 薄緑
    repeat_cell(scenario_sid, 3, 13, 25, 26,
        {"backgroundColor": {"red": 0.85, "green": 0.96, "blue": 0.85}},
        "backgroundColor"),

    # AE列（転記 = 30）: 薄緑
    repeat_cell(scenario_sid, 3, 13, 30, 31,
        {"backgroundColor": {"red": 0.85, "green": 0.96, "blue": 0.85}},
        "backgroundColor"),

    # 元データ ヘッダー行: 太字+青背景
    repeat_cell(meta_sid, 0, 1, 0, 15,
        {"textFormat": {"bold": True},
         "backgroundColor": {"red": 0.63, "green": 0.79, "blue": 0.95}},
        "textFormat,backgroundColor"),

    # シナリオ管理: 行3まで固定
    {"updateSheetProperties": {
        "properties": {"sheetId": scenario_sid, "gridProperties": {"frozenRowCount": 3}},
        "fields": "gridProperties.frozenRowCount",
    }},

    # 元データ: 行1まで固定
    {"updateSheetProperties": {
        "properties": {"sheetId": meta_sid, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount",
    }},

    # C列（広告名）の幅を広げる
    {"updateDimensionProperties": {
        "range": {"sheetId": scenario_sid, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
        "properties": {"pixelSize": 260},
        "fields": "pixelSize",
    }},

    # Y列（シナリオ本文）の幅を広げる
    {"updateDimensionProperties": {
        "range": {"sheetId": scenario_sid, "dimension": "COLUMNS", "startIndex": 24, "endIndex": 25},
        "properties": {"pixelSize": 320},
        "fields": "pixelSize",
    }},

    # O列（停止理由/運用メモ）の幅を広げる
    {"updateDimensionProperties": {
        "range": {"sheetId": scenario_sid, "dimension": "COLUMNS", "startIndex": 14, "endIndex": 15},
        "properties": {"pixelSize": 200},
        "fields": "pixelSize",
    }},
]

api_post(
    f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate",
    {"requests": requests}
)

# ─────────────────────────────────────────
# 完了
# ─────────────────────────────────────────
print("\n" + "=" * 60)
print("完了！")
print(f"URL: {SPREADSHEET_URL}")
print("=" * 60)
print("\n【シート構成】")
print("  ① 元データ  ← Meta広告マネージャーからCSVを貼り付け")
print("     A:キャンペーン名 / C:広告名 / E:IMP / G:COST / H:CT / N:結果(CV) / O:日付")
print("  ② シナリオ管理  ← 集計シート")
print("     B1=集計開始日、B2=集計終了日 を変えると自動集計")
print("     薄緑列（自動計算）: CV,CPA,COST,IMP,CT,CVR,CTR,CPM,文字数,転記")
print("\n【使い方】")
print("  1. Meta広告マネージャーからCSVエクスポート → 元データに貼り付け")
print("  2. シナリオ管理のB1・B2で集計期間を指定")
print("  3. C列（広告名）・B列（CP種別）を入力すると数値が自動集計")
