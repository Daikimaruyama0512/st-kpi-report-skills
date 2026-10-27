"""
マトリクス表の列展開修正スクリプト
A列の1セルにタブ区切りで格納されているデータを、正しいA:E列グリッドに展開する
"""
import sys
import io
import json
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SHEET_ID = "1mcebQCoXe5wd9H_p9lqgnxsuZ0ssZDNF_cgbicMz_dU"
SHEET_NAME = "シート1"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

# 認証
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

BASE_URL = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"

# ---- 現在のA1:A5を読み取り ----
import urllib.parse
encoded = urllib.parse.quote(f"'{SHEET_NAME}'!A1:A5")
r = requests.get(f"{BASE_URL}/values/{encoded}", headers=headers)
r.raise_for_status()
rows = r.json().get("values", [])

print("=== 現在のデータ ===")
for i, row in enumerate(rows, 1):
    val = row[0] if row else ""
    print(f"行{i}: {repr(val)}")

# ---- タブ分割して5列グリッドを構築 ----
grid = []

# C案・D案ラベルの補完マップ
LABEL_FIX = {
    " / 感情訴求型": "C案】やりがい訴求LP / 感情訴求型",
    " / ハードル下げ型": "D案】手軽さ訴求LP / ハードル下げ型",
}

for i, row in enumerate(rows):
    val = row[0] if row else ""
    parts = val.split("\t")

    if i == 0:
        # ヘッダ行: 5値 → A:E
        # parts = [axis, 現行タイプ, シンプル, 口コミ, 数字]
        while len(parts) < 5:
            parts.append("")
        grid.append(parts[:5])
    else:
        # データ行: 4値 → A列(ラベル), B列(空欄), C:E列(3つの形式)
        # parts = [ラベル, シンプル内容, 口コミ内容, 数字内容]
        label = parts[0] if len(parts) > 0 else ""
        # ラベルの欠損を補完
        if label in LABEL_FIX:
            label = LABEL_FIX[label]
        col_c = parts[1] if len(parts) > 1 else ""
        col_d = parts[2] if len(parts) > 2 else ""
        col_e = parts[3] if len(parts) > 3 else ""
        grid.append([label, "", col_c, col_d, col_e])

print("\n=== 変換後のグリッド（A:E） ===")
col_labels = ["A", "B", "C", "D", "E"]
for i, row in enumerate(grid, 1):
    for j, val in enumerate(row):
        if val:
            print(f"  [{i}][{col_labels[j]}]: {val}")

# ---- 確認プロンプト ----
print("\n上記の内容でスプレッドシートを更新します。続行しますか？ [y/N]: ", end="", flush=True)
ans = input().strip().lower()
if ans != "y":
    print("キャンセルしました。")
    sys.exit(0)

# ---- A1:E5 を一括書き込み ----
range_name = f"'{SHEET_NAME}'!A1:E5"
body = {
    "valueInputOption": "USER_ENTERED",
    "data": [
        {
            "range": range_name,
            "values": grid
        }
    ]
}
r2 = requests.post(f"{BASE_URL}/values:batchUpdate", headers=headers, json=body)
r2.raise_for_status()
result = r2.json()
print(f"\n書き込み完了: {result.get('totalUpdatedCells', '?')} セル更新")
print("スプレッドシートを開いて確認してください。")
