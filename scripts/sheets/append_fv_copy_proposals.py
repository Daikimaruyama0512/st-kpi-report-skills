"""
LP改善分析スプシ: FVコピー改善案3パターンを末尾に追記
対象: 1JD-Sj6Kf2yWFOTrVfV9QcwUzDJ0DVum1EwFYLiXi9Lc / LP改善分析タブ
"""
import json
import urllib.request
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_ID = "1JD-Sj6Kf2yWFOTrVfV9QcwUzDJ0DVum1EwFYLiXi9Lc"
TAB_NAME = "LP改善分析"
START_ROW = 76  # 74行目まで既存コンテンツ + 空行1

# ---- 認証 ----
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
TOKEN = creds.token


def api_post(url, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())


def get_sheet_id():
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets.properties"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
    for s in data["sheets"]:
        if s["properties"]["title"] == TAB_NAME:
            return s["properties"]["sheetId"]
    raise ValueError(f"タブ '{TAB_NAME}' が見つかりません")


# ---- 書き込むデータ ----
rows = [
    # 空行
    [""],
    # ===== セクションヘッダー =====
    ["FVコピー改善案（訴求軸データ根拠版・2026-07-26）"],
    # 背景説明
    ["【根拠データ】直近90日BigQuery分析より: やりがい訴求は不在。主流はFOMO/損失回避。"],
    ["最高CPA広告: 01タイパ_見えない損失の可視化_ペルソナLP (CPA 9,090円 / spend 182K)"],
    [""],
    # ===== パターンA =====
    ["パターンA: 損失回避型"],
    ["対応広告", "見えない損失の可視化（CPA 9,090円）・タイパセグメント向け"],
    ["H1", "同じ週3コマでも、塾を間違えると月1万円損する。"],
    ["サブコピー", "どの塾を選ぶかで、時給・シフト・続けやすさが全部変わる。LINEで1分診断して、自分に合う塾を先に知っておく。"],
    ["CTA", "無料で診断する（1分）"],
    ["補足テキスト", "LINE登録 / 会員登録不要 / すぐ結果を表示"],
    ["FVの狙い", "損失を「月1万円」という具体数字で可視化。知らずに損する怖さ→診断で防げるという構造。"],
    [""],
    # ===== パターンB =====
    ["パターンB: タイミングFOMO型"],
    ["対応広告", "夏期講習先行確保（spend 505K）・乗り遅れ（spend 785K）・7月下旬の季節変数に直接対応"],
    ["H1", "夏期講習の塾バイト、もう動いてる人がいる。"],
    ["サブコピー", "良い条件の枠は、先に診断した人から決まる。全国2,000社以上の中から、今すぐLINEで確認。"],
    ["CTA", "LINEで今すぐ確認する"],
    ["補足テキスト", "1分・無料・すぐ求人を表示"],
    ["FVの狙い", "「もう動いてる人がいる」で比較・競争心を刺激。今が旬の季節変数（夏期講習）と直結。"],
    [""],
    # ===== パターンC =====
    ["パターンC: 安心・ミスマッチ防止型"],
    ["対応広告", "学力が不安でも大丈夫（CPA 11,117円）・まだ探せていない焦り（CPA 14,259円）・単願セグメント向け"],
    ["H1", "塾バイト、入ってから「思ってたのと違う」は避けたい。"],
    ["サブコピー", "3問答えるだけで、自分に合う塾タイプがわかる。学力・シフト・距離の不安は、診断してから解消する。"],
    ["CTA", "無料で3問診断する"],
    ["補足テキスト", "LINE登録1分 / 登録後すぐ結果"],
    ["FVの狙い", "「失敗したくない」心理を先制解消。慎重に選ぶ単願型に刺さりやすい。診断への参入ハードルが最も低い。"],
    [""],
    # ===== 比較テーブル =====
    ["パターン比較"],
    ["パターン", "対応広告（例）", "ユーザー心理", "FVの役割", "推奨CTA先"],
    ["A: 損失回避型", "見えない損失の可視化", "損している自覚がない", "損失を数字で気づかせる", "ペルソナLP"],
    ["B: タイミングFOMO型", "夏期講習先行確保・乗り遅れ", "出遅れへの焦り", "今すぐ動く理由を作る", "ブランド診断 or ペルソナLP"],
    ["C: 安心・ミスマッチ防止型", "学力不安・まだ探せていない焦り", "失敗回避・慎重", "診断で安全に一歩踏み出せる", "ブランド診断"],
    [""],
    ["【運用メモ】1本に絞るなら A（データ根拠最強）。広告セグメント別出し分けならA（タイパ向け）＋C（単願向け）が現実的。"],
]

# ---- 値の書き込み ----
range_str = f"'{TAB_NAME}'!A{START_ROW}"
url_values = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchUpdate"
api_post(url_values, {
    "valueInputOption": "USER_ENTERED",
    "data": [{"range": range_str, "values": rows}],
})
print("値の書き込み完了")

# ---- フォーマット ----
sheet_id = get_sheet_id()

def rgb(r, g, b):
    return {"red": r / 255, "green": g / 255, "blue": b / 255}

def repeat_cell(row_idx, num_cols, bg, bold=False, font_size=11, text_color=None):
    tc = text_color or rgb(255, 255, 255)
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": bg,
                    "textFormat": {
                        "bold": bold,
                        "fontSize": font_size,
                        "foregroundColor": tc,
                    },
                    "wrapStrategy": "WRAP",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)",
        }
    }

# 行インデックス（0始まり）
r = START_ROW - 1  # 0-indexed

fmt_requests = []

# 空行(r+0) スキップ
# セクションヘッダー(r+1)
fmt_requests.append(repeat_cell(r + 1, 4, rgb(26, 26, 46), bold=True, font_size=12))
# 背景説明(r+2, r+3) - 薄いグレー
for i in [2, 3]:
    fmt_requests.append(repeat_cell(r + i, 4, rgb(240, 240, 240), bold=False, text_color=rgb(50, 50, 50)))

# パターンA ヘッダー(r+5)
fmt_requests.append(repeat_cell(r + 5, 4, rgb(45, 106, 79), bold=True))
# パターンA 項目行(r+6〜r+12): 項目名列（A列）に薄緑背景
for i in range(6, 12):
    fmt_requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": r + i, "endRowIndex": r + i + 1,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": rgb(216, 243, 220),
                "textFormat": {"bold": True, "foregroundColor": rgb(30, 30, 30)},
                "wrapStrategy": "WRAP",
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)",
        }
    })

# パターンB ヘッダー(r+13) ← 空行r+12の次
fmt_requests.append(repeat_cell(r + 13, 4, rgb(45, 106, 79), bold=True))
for i in range(14, 20):
    fmt_requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": r + i, "endRowIndex": r + i + 1,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": rgb(216, 243, 220),
                "textFormat": {"bold": True, "foregroundColor": rgb(30, 30, 30)},
                "wrapStrategy": "WRAP",
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)",
        }
    })

# パターンC ヘッダー(r+21)
fmt_requests.append(repeat_cell(r + 21, 4, rgb(45, 106, 79), bold=True))
for i in range(22, 28):
    fmt_requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": r + i, "endRowIndex": r + i + 1,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": rgb(216, 243, 220),
                "textFormat": {"bold": True, "foregroundColor": rgb(30, 30, 30)},
                "wrapStrategy": "WRAP",
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)",
        }
    })

# 比較テーブルヘッダー(r+29)
fmt_requests.append(repeat_cell(r + 29, 5, rgb(26, 26, 46), bold=True, font_size=12))
# 比較テーブル列ヘッダー(r+30)
fmt_requests.append(repeat_cell(r + 30, 5, rgb(69, 123, 157), bold=True))
# 比較テーブルデータ行(r+31〜r+33): 交互
for i, idx in enumerate([31, 32, 33]):
    bg = rgb(235, 245, 251) if i % 2 == 0 else rgb(255, 255, 255)
    fmt_requests.append(repeat_cell(r + idx, 5, bg, bold=False, text_color=rgb(30, 30, 30)))

# 運用メモ(r+35)
fmt_requests.append(repeat_cell(r + 35, 5, rgb(255, 243, 205), bold=False, text_color=rgb(50, 50, 50)))

# 列幅調整（B列を広く）
fmt_requests.append({
    "updateDimensionProperties": {
        "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
        "properties": {"pixelSize": 420},
        "fields": "pixelSize",
    }
})
fmt_requests.append({
    "updateDimensionProperties": {
        "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
        "properties": {"pixelSize": 160},
        "fields": "pixelSize",
    }
})

url_fmt = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
api_post(url_fmt, {"requests": fmt_requests})
print("フォーマット適用完了")

print()
print("=" * 60)
print("LP改善分析 追記完了")
print(f"URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit?gid=812087031#gid=812087031")
print("=" * 60)
