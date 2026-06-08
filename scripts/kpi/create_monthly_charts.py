# scripts/create_monthly_charts.py
# 月次KPIトレンドチャート 初期作成スクリプト（初回1回だけ実行）
# 実行後は kpi_report_st.py --write で月次データが自動更新される
#
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth google-api-python-client
#
# 使い方:
#   初回作成:  python3 scripts/create_monthly_charts.py
#   スタイル更新: python3 scripts/create_monthly_charts.py --update

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery
from googleapiclient.discovery import build

TOKEN_FILE     = "/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
PROJECT_ID     = "bigquery-jukust"
BQ_VIEW        = "bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report"
SPREADSHEET_ID = "1xXeCl4Xbkxz-w_jT49TmA3-voruL2cTbF1f308hZ5vQ"
KPI_COPY_TAB   = "KPI報告 のコピー"

# 列定義（0-indexed）
# AL(37) = ラベル列、AM(38)-AR(43) = データ列（6ヶ月分）
LABEL_COL_IDX  = 37   # AL
DATA_COL_START = 38   # AM
NUM_MONTHS     = 6    # 直近6ヶ月
DATA_COL_END   = DATA_COL_START + NUM_MONTHS  # exclusive: 44

# 行定義（0-indexed, シート上の行番号 - 1）
ROW_HEADER   = 1   # 行2: 月ラベル
ROW_LINE_CV  = 2   # 行3: LINE登録CV
ROW_OBO_CV   = 3   # 行4: 応募CV（※custom_cv_2バグのため空）
ROW_OBO_CPA  = 4   # 行5: 応募CPA（※同上）
ROW_COST     = 5   # 行6: COST
ROW_CPF      = 6   # 行7: CPF（LINE登録CPA）
ROW_CTR      = 7   # 行8: CTR(%)
ROW_CVR      = 8   # 行9: CVR(%)
ROW_CPM      = 9   # 行10: CPM

KPI_ROWS = [
    {'name': 'LINE登録CV', 'row': ROW_LINE_CV},
    {'name': '応募CV',     'row': ROW_OBO_CV},
    {'name': '応募CPA',    'row': ROW_OBO_CPA},
    {'name': 'COST',       'row': ROW_COST},
    {'name': 'CPF',        'row': ROW_CPF},
    {'name': 'CTR(%)',     'row': ROW_CTR},
    {'name': 'CVR(%)',     'row': ROW_CVR},
    {'name': 'CPM',        'row': ROW_CPM},
]

# ── チャートスタイル定数 ──────────────────────────
CHART_WIDTH_PX  = 520   # 450 → 520
CHART_HEIGHT_PX = 320   # 280 → 320

# 8KPI の線色（Google Sheets API rgbColor 形式: red/green/blue 各 0.0-1.0）
KPI_COLORS = [
    {"red": 0.024, "green": 0.780, "blue": 0.333},  # LINE登録CV: LINE緑
    {"red": 0.000, "green": 0.537, "blue": 0.482},  # 応募CV:     青緑
    {"red": 0.957, "green": 0.318, "blue": 0.118},  # 応募CPA:    オレンジ赤
    {"red": 0.827, "green": 0.184, "blue": 0.184},  # COST:       赤
    {"red": 0.984, "green": 0.549, "blue": 0.000},  # CPF:        橙
    {"red": 0.482, "green": 0.122, "blue": 0.635},  # CTR(%):     紫
    {"red": 0.086, "green": 0.396, "blue": 0.753},  # CVR(%):     青
    {"red": 0.329, "green": 0.431, "blue": 0.478},  # CPM:        グレー青
]

# Y軸 NumberFormat パターン（KPI別）
# CTR/CVR: BQで *100 して格納しているため "0.00%" は不可（0.01倍される）→ "#,##0.00" + タイトルで単位表示
KPI_AXIS_FORMAT = [
    "#,##0",      # LINE登録CV（件）
    "#,##0",      # 応募CV（件）
    "¥#,##0",     # 応募CPA
    "¥#,##0",     # COST
    "¥#,##0",     # CPF
    "#,##0.00",   # CTR(%) ← 値は整数%（例: 1.23）
    "#,##0.00",   # CVR(%) ← 同上
    "¥#,##0",     # CPM
]

# チャート配置（4列×2行レイアウト, O29起点）
# O = 14 (0-indexed),  row29 = 28 (0-indexed)
# 各チャートを9列・15行間隔で配置
CHART_ANCHORS = [
    # (col_idx, row_idx) ← 0-indexed
    (14, 28),   # LINE登録CV: O29
    (23, 28),   # 応募CV:     X29
    (32, 28),   # 応募CPA:    AG29
    (41, 28),   # COST:       AP29
    (14, 43),   # CPF:        O44
    (23, 43),   # CTR:        X44
    (32, 43),   # CVR:        AG44
    (41, 43),   # CPM:        AP44
]

SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/spreadsheets',
]


def col_letter(idx):
    """0-indexed列番号 → 列文字（例: 38 → 'AM'）"""
    result = ''
    idx += 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        result = chr(65 + r) + result
    return result


def fetch_monthly_data(bq_client):
    """BQから直近6ヶ月の月次集計データを取得"""
    query = f"""
WITH monthly AS (
  SELECT
    FORMAT_DATE('%m月', DATE_TRUNC(target_date, MONTH)) AS month_label,
    DATE_TRUNC(target_date, MONTH) AS month_date,
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS line_cv,
    SUM(link_clicks)           AS link_clicks,
    SUM(impressions)           AS impressions
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 5 MONTH), MONTH)
  GROUP BY 1, 2
)
SELECT
  month_label,
  line_cv,
  SAFE_DIVIDE(spend, NULLIF(line_cv, 0))                AS cpf,
  spend,
  SAFE_DIVIDE(link_clicks, NULLIF(impressions, 0)) * 100 AS ctr,
  SAFE_DIVIDE(line_cv, NULLIF(link_clicks, 0))     * 100 AS cvr,
  SAFE_DIVIDE(spend, NULLIF(impressions, 0))       * 1000 AS cpm
FROM monthly
ORDER BY month_date
"""
    rows = list(bq_client.query(query).result())
    data = []
    for r in rows:
        data.append({
            'month_label': r['month_label'],
            'line_cv':     int(r['line_cv'] or 0),
            'cpf':         round(float(r['cpf']), 0) if r['cpf'] else '',
            'spend':       round(float(r['spend'] or 0), 0),
            'ctr':         round(float(r['ctr']), 2)  if r['ctr'] else '',
            'cvr':         round(float(r['cvr']), 2)  if r['cvr'] else '',
            'cpm':         round(float(r['cpm']), 0)  if r['cpm'] else '',
        })
    return data


def write_monthly_data(svc, monthly_data):
    """AL2:AR10 に月次データを書き込む（ラベル列 + 6ヶ月分）"""
    months = [d['month_label'] for d in monthly_data]
    sheet_data = [
        ['月']         + months,
        ['LINE登録CV'] + [d['line_cv'] for d in monthly_data],
        ['応募CV']     + ['' for _ in monthly_data],  # custom_cv_2バグのため空
        ['応募CPA']    + ['' for _ in monthly_data],  # 同上
        ['COST']       + [d['spend']  for d in monthly_data],
        ['CPF']        + [d['cpf']    for d in monthly_data],
        ['CTR(%)']     + [d['ctr']    for d in monthly_data],
        ['CVR(%)']     + [d['cvr']    for d in monthly_data],
        ['CPM']        + [d['cpm']    for d in monthly_data],
    ]
    start_col = col_letter(LABEL_COL_IDX)  # AL
    end_col   = col_letter(DATA_COL_START + len(monthly_data) - 1)  # AR（月数に応じて）

    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{KPI_COPY_TAB}'!{start_col}2:{end_col}10",
        valueInputOption='USER_ENTERED',
        body={'values': sheet_data}
    ).execute()
    print(f"  書き込み完了: {start_col}2:{end_col}10 ({len(monthly_data)}ヶ月: {', '.join(months)})")


def get_existing_chart_ids(svc, sheet_id):
    """対象シートの既存チャートID一覧を返す"""
    sheet_meta = svc.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for s in sheet_meta['sheets']:
        if s['properties']['sheetId'] == sheet_id:
            charts = s.get('charts', [])
            return [c['chartId'] for c in charts]
    return []


def delete_charts(svc, chart_ids):
    """指定chartIdのチャートを一括削除"""
    if not chart_ids:
        print("  削除対象チャートなし")
        return
    requests = [
        {"deleteEmbeddedObject": {"objectId": cid}}
        for cid in chart_ids
    ]
    svc.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests}
    ).execute()
    print(f"  {len(chart_ids)}本のチャートを削除しました")


def create_charts(svc, sheet_id, num_months):
    """8本の月次折れ線グラフを作成"""
    requests = []
    for i, kpi in enumerate(KPI_ROWS):
        col_idx, row_idx = CHART_ANCHORS[i]
        color  = KPI_COLORS[i]
        fmt    = KPI_AXIS_FORMAT[i]
        requests.append({
            "addChart": {
                "chart": {
                    "spec": {
                        "title": f"{kpi['name']} 月次推移",
                        "titleTextFormat": {"fontSize": 12, "bold": True},
                        "basicChart": {
                            "chartType": "COMBO",
                            "legendPosition": "NO_LEGEND",
                            "lineSmoothing": True,
                            "axis": [
                                {"position": "BOTTOM_AXIS"},
                                {
                                    "position": "LEFT_AXIS",
                                    "title": kpi['name'],
                                    "format": {
                                        "pattern": fmt
                                    }
                                },
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId":          sheet_id,
                                                    "startRowIndex":    ROW_HEADER,
                                                    "endRowIndex":      ROW_HEADER + 1,
                                                    "startColumnIndex": DATA_COL_START,
                                                    "endColumnIndex":   DATA_COL_START + num_months,
                                                }
                                            ]
                                        }
                                    }
                                }
                            ],
                            "series": [
                                {
                                    "series": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId":          sheet_id,
                                                    "startRowIndex":    kpi['row'],
                                                    "endRowIndex":      kpi['row'] + 1,
                                                    "startColumnIndex": DATA_COL_START,
                                                    "endColumnIndex":   DATA_COL_START + num_months,
                                                }
                                            ]
                                        }
                                    },
                                    "targetAxis": "LEFT_AXIS",
                                    "type": "LINE",
                                    "colorStyle": {
                                        "rgbColor": color
                                    },
                                    "lineStyle": {
                                        "width": 3,
                                        "type": "SOLID"
                                    },
                                    "pointStyle": {
                                        "shape": "CIRCLE",
                                        "size": 8
                                    },
                                    "dataLabel": {
                                        "type": "DATA",
                                        "placement": "ABOVE",
                                        "textFormat": {
                                            "fontSize": 9,
                                            "bold": False
                                        }
                                    }
                                }
                            ],
                            "headerCount": 0
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId":     sheet_id,
                                "rowIndex":    row_idx,
                                "columnIndex": col_idx,
                            },
                            "offsetXPixels": 0,
                            "offsetYPixels": 0,
                            "widthPixels":   CHART_WIDTH_PX,
                            "heightPixels":  CHART_HEIGHT_PX,
                        }
                    }
                }
            }
        })

    svc.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests}
    ).execute()
    print(f"  {len(requests)}本のチャートを作成しました")


def main():
    update_mode = '--update' in sys.argv

    print("=== 月次KPIチャート作成スクリプト ===")
    print(f"  モード: {'スタイル更新 (--update)' if update_mode else '初回作成'}")
    print(f"  シート: {SPREADSHEET_ID}")
    print(f"  タブ: {KPI_COPY_TAB}")

    # 認証
    print("\n=== 認証 ===")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    print("  OK")

    sheets_svc = build('sheets', 'v4', credentials=creds)

    # タブのシートID取得
    sheet_meta = sheets_svc.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    kpi_copy_sheet_id = None
    for s in sheet_meta['sheets']:
        if s['properties']['title'] == KPI_COPY_TAB:
            kpi_copy_sheet_id = s['properties']['sheetId']
            break

    if kpi_copy_sheet_id is None:
        print(f"[エラー] '{KPI_COPY_TAB}' タブが見つかりません")
        sys.exit(1)
    print(f"  シートID: {kpi_copy_sheet_id}")

    if update_mode:
        # --update: 既存チャートを削除して新スタイルで再作成
        print("\n=== 既存チャート削除 ===")
        existing_ids = get_existing_chart_ids(sheets_svc, kpi_copy_sheet_id)
        print(f"  発見したチャート: {len(existing_ids)}本")
        delete_charts(sheets_svc, existing_ids)

        # BQクエリはスキップ（データはシートに残っているため）
        num_months = NUM_MONTHS
    else:
        # 通常モード: 既存チャートがある場合は警告してスキップ
        existing_ids = get_existing_chart_ids(sheets_svc, kpi_copy_sheet_id)
        if existing_ids:
            print(f"\n[警告] チャートが既に {len(existing_ids)}本 存在します。")
            print("  スタイルを更新したい場合は --update フラグを使ってください:")
            print("  python3 scripts/create_monthly_charts.py --update")
            sys.exit(0)

        # BQデータ取得
        print("\n=== BQ月次データ取得（直近6ヶ月）===")
        bq_client = bigquery.Client(project=PROJECT_ID, credentials=creds)
        monthly_data = fetch_monthly_data(bq_client)
        if not monthly_data:
            print("[エラー] BQからデータが取得できませんでした")
            sys.exit(1)
        for d in monthly_data:
            print(f"  {d['month_label']}: LINE_CV={d['line_cv']}, spend={int(d['spend']):,}, CPF={d['cpf'] or 'N/A'}")

        # データ書き込み
        print("\n=== シートへデータ書き込み ===")
        write_monthly_data(sheets_svc, monthly_data)
        num_months = len(monthly_data)

    # チャート作成
    print("\n=== チャート作成（8本）===")
    create_charts(sheets_svc, kpi_copy_sheet_id, num_months)

    print("\n完了。")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={kpi_copy_sheet_id}")
    if not update_mode:
        print("\n次回以降は以下コマンドで月次データが自動更新されます:")
        print("  python3 scripts/kpi_report_st.py 2026/MM/DD-2026/MM/DD --write")


if __name__ == '__main__':
    main()
