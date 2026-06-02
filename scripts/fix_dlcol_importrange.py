"""
KPI報告のコピー D12:L59 REFエラー修正スクリプト
'週次'!$E...:... を直接参照するXLOOKUP式をIMPORTRANGEパターンに置換する。
"""
import re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import os as _os
_HERE      = _os.path.dirname(_os.path.abspath(__file__))
TOKEN_FILE = _os.path.join(_os.path.dirname(_HERE), "secrets", "token.json")

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

KPI_SHEET_ID   = '1xXeCl4Xbkxz-w_jT49TmA3-voruL2cTbF1f308hZ5vQ'
SHUUJI_ID      = '1QWJsnc-JKn-1fcjZMUygsccZXuygt4e9wY71bnxuSyQ'
COPY_SHEET     = 'KPI報告 のコピー'
TARGET_RANGE   = f"'{COPY_SHEET}'!D12:L59"

# 数式中の行番号を抽出するパターン
# 例: =XLOOKUP(D$6,'週次'!$E$5:$5,'週次'!$E7:7,false)
#                                              ^^^ ここを取る
PATTERN = re.compile(
    r"=XLOOKUP\(([A-L]\$6),'週次'!\$E\$5:\$5,'週次'!\$E(\d+):\d+,false\)",
    re.IGNORECASE
)

def col_letter(zero_based_idx):
    """0始まりの列インデックス → A1記法の列文字（A=0, B=1, ...）"""
    result = ''
    idx = zero_based_idx + 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        result = chr(65 + r) + result
    return result

def main():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    svc   = build('sheets', 'v4', credentials=creds)
    sheet = svc.spreadsheets()

    # 1. 現在の数式を取得
    resp = sheet.values().get(
        spreadsheetId=KPI_SHEET_ID,
        range=TARGET_RANGE,
        valueRenderOption='FORMULA'
    ).execute()

    rows = resp.get('values', [])
    if not rows:
        print("データなし: 範囲が空")
        return

    # D12 が row_offset=12, col_offset=3(D=0のA起点)
    ROW_START = 12
    COL_START = 3   # D=3 (A=0)

    updates = []
    match_count   = 0
    skip_count    = 0

    for row_idx, row in enumerate(rows):
        for col_idx, cell_formula in enumerate(row):
            if not isinstance(cell_formula, str):
                continue
            m = PATTERN.match(cell_formula)
            if not m:
                skip_count += 1
                continue

            lookup_key  = m.group(1)   # 例: D$6
            bq_row      = m.group(2)   # 例: 7

            new_formula = (
                f'=IFERROR(XLOOKUP({lookup_key},'
                f'IMPORTRANGE("{SHUUJI_ID}","週次!E5:GF5"),'
                f'IMPORTRANGE("{SHUUJI_ID}","週次!E{bq_row}:GF{bq_row}")),"--")'
            )

            # A1記法でセルアドレスを計算
            sheet_row = ROW_START + row_idx          # 1始まり行番号
            sheet_col = COL_START + col_idx          # 0始まり列インデックス
            cell_addr = f"'{COPY_SHEET}'!{col_letter(sheet_col)}{sheet_row}"

            updates.append({
                'range':  cell_addr,
                'values': [[new_formula]]
            })
            match_count += 1

    if not updates:
        print("置換対象のXLOOKUP式が見つかりませんでした")
        print(f"スキャン済みセル数: {sum(len(r) for r in rows)}")
        # デバッグ: 最初の数セルを表示
        for i, row in enumerate(rows[:3]):
            for j, v in enumerate(row[:3]):
                print(f"  [{i}][{j}]: {repr(v)[:80]}")
        return

    print(f"置換対象: {match_count} セル / スキャン: {sum(len(r) for r in rows)} セル")

    # 2. 一括書き込み
    CHUNK = 50
    written = 0
    for i in range(0, len(updates), CHUNK):
        chunk = updates[i:i+CHUNK]
        sheet.values().batchUpdate(
            spreadsheetId=KPI_SHEET_ID,
            body={'valueInputOption': 'USER_ENTERED', 'data': chunk}
        ).execute()
        written += len(chunk)
        print(f"  書き込み: {written}/{len(updates)} セル完了")

    print(f"\n完了。{match_count} 件のXLOOKUP式をIMPORTRANGEパターンに置換した。")

if __name__ == '__main__':
    main()
