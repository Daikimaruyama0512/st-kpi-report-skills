#!/usr/bin/env python3
"""
ST Meta KPI報告シート（BQ版）新規作成スクリプト
集計さんの「KPI報告」タブと同じ行構造を持つ独立したスプレッドシートを作成する。
データソース: BigQuery（kpi_report_st.py --write-new で書き込み）
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = '/Users/119322/Desktop/claude-code-template_af/secrets/token.json'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

# データ列: D〜M（10週分）、シード: O1/P1/Q1
DATA_COLS = ['D','E','F','G','H','I','J','K','L','M']
SEED_COL  = 'M'   # 最新週の列
SEED_YEAR  = 'O'  # O1: 年（例 "2026年"）
SEED_MONTH = 'P'  # P1: 月（例 "5月"）
SEED_WEEK  = 'Q'  # Q1: 週（例 "W4"）


def data_range(row):
    return f'KPI報告!D{row}:{DATA_COLS[-1]}{row}'


def build_row7(cols):
    """年ラベル自動生成（1月またぎで年を-1）"""
    result = []
    for i, col in enumerate(cols):
        if col == SEED_COL:
            result.append(f'={SEED_YEAR}1')
        else:
            nc = cols[i + 1]
            result.append(
                f'=if({nc}8="1月",if({col}8={nc}8,{nc}7,(left({nc}7,4)-1)&"年"),{nc}7)'
            )
    return result


def build_row8(cols):
    """月ラベル自動生成（W1またぎで月を-1、12月→1月の折り返し対応）"""
    result = []
    for i, col in enumerate(cols):
        if col == SEED_COL:
            result.append(f'={SEED_MONTH}1')
        else:
            nc = cols[i + 1]
            result.append(
                f'=if(if({nc}9="W1",(left({nc}8,1)-1)&"月",{nc}8)="0月",'
                f'if({nc}8="1月","12月",if({nc}8="12月","11月",if({nc}8="11月","10月","9月"))),'
                f'if({nc}9="W1",(left({nc}8,1)-1)&"月",{nc}8))'
            )
    return result


def build_row9(cols):
    """週ラベル自動生成（W1の前はW4）"""
    result = []
    for i, col in enumerate(cols):
        if col == SEED_COL:
            result.append(f'={SEED_WEEK}1')
        else:
            nc = cols[i + 1]
            result.append(f'="W"&if({nc}9="W1",4,right({nc}9,1)-1)')
    return result


def build_formula_row(cols, template):
    """テンプレート文字列の {col} を各列名に置換してリストを返す"""
    return [template.replace('{col}', c) for c in cols]


def main():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    print("スプレッドシートを作成中...")
    spreadsheet = service.spreadsheets().create(body={
        'properties': {'title': 'ST Meta KPI報告 (BQ版)'},
        'sheets': [
            {'properties': {'title': 'KPI報告', 'sheetId': 0, 'index': 0}},
            {'properties': {'title': '入力',    'sheetId': 1, 'index': 1}},
        ]
    }).execute()

    ss_id = spreadsheet['spreadsheetId']
    print(f"  作成完了: {ss_id}")

    # ======================================================
    # KPI報告タブ セルデータ定義
    # ======================================================
    data = [
        # ---- シード（TODAY()から自動計算） ----
        {'range': f'KPI報告!{SEED_YEAR}1',  'values': [['=TEXT(TODAY(),"YYYY")&"年"']]},
        {'range': f'KPI報告!{SEED_MONTH}1', 'values': [['=MONTH(TODAY())&"月"']]},
        {'range': f'KPI報告!{SEED_WEEK}1',  'values': [['="W"&MIN(ROUNDUP(DAY(TODAY())/7,0),4)']]},
        {'range': 'KPI報告!S1',  'values': [['=DAY(TODAY()-1)/DAY(EOMONTH(TODAY()-1,0))']]},

        # ---- タイトル行 ----
        {'range': 'KPI報告!B2', 'values': [['全体']]},

        # ---- 日付ヘッダー行（行6〜10） ----
        {'range': data_range(6),  'values': [build_formula_row(DATA_COLS, '={col}7&{col}8&{col}9')]},
        {'range': data_range(7),  'values': [build_row7(DATA_COLS)]},
        {'range': data_range(8),  'values': [build_row8(DATA_COLS)]},
        {'range': data_range(9),  'values': [build_row9(DATA_COLS)]},
        {'range': data_range(10), 'values': [build_formula_row(DATA_COLS, '={col}8&{col}9')]},

        # ---- 行ラベル（C列） ----
        {'range': 'KPI報告!C10', 'values': [['月週']]},
        {'range': 'KPI報告!C11', 'values': [['CV']]},
        {'range': 'KPI報告!C12', 'values': [['転換率 ※概算指標']]},
        {'range': 'KPI報告!C13', 'values': [['CT']]},
        {'range': 'KPI報告!C14', 'values': [['CPA※遅行指標']]},
        {'range': 'KPI報告!C15', 'values': [['LINE_CV']]},
        {'range': 'KPI報告!C16', 'values': [['目標']]},
        {'range': 'KPI報告!C17', 'values': [['CT']]},
        {'range': 'KPI報告!C19', 'values': [['IMP']]},
        {'range': 'KPI報告!C21', 'values': [['リーチ ※BQ未対応']]},
        {'range': 'KPI報告!C23', 'values': [['フリークエンシー ※BQ未対応']]},
        {'range': 'KPI報告!C25', 'values': [['CPA（LINE登録）']]},
        {'range': 'KPI報告!C26', 'values': [['応募CPA']]},
        {'range': 'KPI報告!C27', 'values': [['COST']]},
        {'range': 'KPI報告!C29', 'values': [['CPC']]},
        {'range': 'KPI報告!C30', 'values': [['CPM']]},
        {'range': 'KPI報告!C32', 'values': [['CVR']]},
        {'range': 'KPI報告!C34', 'values': [['CTR']]},

        # ---- LINE応募・友だち数セクション ----
        {'range': 'KPI報告!B35', 'values': [['LINE応募']]},
        {'range': 'KPI報告!C35', 'values': [['応募目標']]},
        {'range': 'KPI報告!C36', 'values': [['応募昨年']]},
        {'range': 'KPI報告!C37', 'values': [['目標比']]},
        {'range': 'KPI報告!B38', 'values': [['全体_LINE友だち数']]},
        {'range': 'KPI報告!C38', 'values': [['[全体]LINE_CV']]},
        {'range': 'KPI報告!C39', 'values': [['目標']]},
        {'range': 'KPI報告!C40', 'values': [['目標比']]},
        {'range': 'KPI報告!C41', 'values': [['Meta目標']]},
        {'range': 'KPI報告!C42', 'values': [['Meta目標比']]},

        # ---- CTA別LINE登録（行44〜53） ----
        {'range': 'KPI報告!B44', 'values': [['▽CTA別LINE登録']]},
        {'range': 'KPI報告!B45', 'values': [['ペルソナLP']]},        {'range': 'KPI報告!C45', 'values': [['CV']]},
        {'range': 'KPI報告!B46', 'values': [['塾ブランド診断のみ']]}, {'range': 'KPI報告!C46', 'values': [['CV']]},
        {'range': 'KPI報告!B47', 'values': [['気軽に診断']]},        {'range': 'KPI報告!C47', 'values': [['CV']]},
        {'range': 'KPI報告!B48', 'values': [['新1年生']]},           {'range': 'KPI報告!C48', 'values': [['CV']]},
        {'range': 'KPI報告!B49', 'values': [['SNS ORG']]},           {'range': 'KPI報告!C49', 'values': [['CV']]},
        {'range': 'KPI報告!B50', 'values': [['ペルソナLP']]},        {'range': 'KPI報告!C50', 'values': [['COST']]},
        {'range': 'KPI報告!B51', 'values': [['塾ブランド診断のみ']]}, {'range': 'KPI報告!C51', 'values': [['COST']]},
        {'range': 'KPI報告!B52', 'values': [['気軽に診断']]},        {'range': 'KPI報告!C52', 'values': [['COST']]},
        {'range': 'KPI報告!B53', 'values': [['新1年生']]},           {'range': 'KPI報告!C53', 'values': [['COST']]},

        # ---- CTA別応募CV（行54〜58） ----
        {'range': 'KPI報告!B54', 'values': [['ペルソナLP']]},        {'range': 'KPI報告!C54', 'values': [['応募CV']]},
        {'range': 'KPI報告!B55', 'values': [['塾ブランド診断']]},    {'range': 'KPI報告!C55', 'values': [['応募CV']]},
        {'range': 'KPI報告!B56', 'values': [['気軽に診断']]},        {'range': 'KPI報告!C56', 'values': [['応募CV']]},
        {'range': 'KPI報告!B57', 'values': [['新1年生']]},           {'range': 'KPI報告!C57', 'values': [['応募CV']]},
        {'range': 'KPI報告!B58', 'values': [['ORG']]},               {'range': 'KPI報告!C58', 'values': [['応募CV']]},

        # ---- 経路別CPA ----
        {'range': 'KPI報告!B59', 'values': [['▽経路別応募CPA']]},
        {'range': 'KPI報告!C60', 'values': [['ペルソナLP']]},

        # ---- 派生指標（シート内数式） ----
        # 行12: 転換率 = 応募CV / LINE_CV
        {'range': data_range(12), 'values': [build_formula_row(DATA_COLS, '=IFERROR({col}11/{col}15,"-")')]},
        # 行29: CPC = COST / CT（link_clicks）
        {'range': data_range(29), 'values': [build_formula_row(DATA_COLS, '=IFERROR({col}27/{col}17,"-")')]},
        # 行30: CPM = COST / IMP * 1000
        {'range': data_range(30), 'values': [build_formula_row(DATA_COLS, '=IFERROR({col}27/{col}19*1000,"-")')]},
        # 行32: CVR = LINE_CV / CT
        {'range': data_range(32), 'values': [build_formula_row(DATA_COLS, '=IFERROR({col}15/{col}17,"-")')]},
        # 行34: CTR = CT / IMP
        {'range': data_range(34), 'values': [build_formula_row(DATA_COLS, '=IFERROR({col}17/{col}19,"-")')]},
        # 行60: 経路別応募CPA（ペルソナLP）= ペルソナLP COST / ペルソナLP 応募CV
        {'range': data_range(60), 'values': [build_formula_row(DATA_COLS, '=IFERROR({col}50/{col}54,"-")')]},
    ]

    print("KPI報告タブを構築中...")
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=ss_id,
        body={'valueInputOption': 'USER_ENTERED', 'data': data}
    ).execute()

    # ======================================================
    # 入力タブ（予算・目標）
    # ======================================================
    input_data = [
        {'range': '入力!A1', 'values': [['月', '月間予算（円）', 'LINE登録CV目標', '応募CV目標']]},
        {'range': '入力!A2', 'values': [['5月', 2000000, '', '']]},
        {'range': '入力!A3', 'values': [['6月', '', '', '']]},
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=ss_id,
        body={'valueInputOption': 'USER_ENTERED', 'data': input_data}
    ).execute()

    print("入力タブを構築中...")
    print()
    print("=" * 60)
    print(f"✅ 作成完了")
    print(f"   ID : {ss_id}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{ss_id}")
    print()
    print("次のステップ:")
    print("  kpi_report_st.py の NEW_KPI_SPREADSHEET_ID にこのIDを設定")
    print("  python3 scripts/kpi_report_st.py 2026/MM/DD-2026/MM/DD --write --new-sheet")
    print("=" * 60)


if __name__ == '__main__':
    main()
