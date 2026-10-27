# LPO ABテスト分析：ブランド診断LP
# 同一クリエイティブでLPのみ変更したABテスト
# 構成:
#   Creative1: 夏の予定優先×働きやすさ  LP-A vs LP-B
#   Creative2: 夏期講習の先行確保       LP-A vs LP-B
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth-oauthlib google-api-python-client

import sys, io
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.cloud import bigquery
from googleapiclient.discovery import build

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
PROJECT_ID = "bigquery-jukust"
SPREADSHEET_ID = "1JD-Sj6Kf2yWFOTrVfV9QcwUzDJ0DVum1EwFYLiXi9Lc"
SHEET_GID = "468902428"

# ABテスト対象広告（LP-AとLP-Bのペア × 2クリエイティブ）
PAIRS = [
    {
        "creative": "夏の予定優先×働きやすさ",
        "lp_a": "01タイパ_夏の予定優先×働きやすさ_ブランド診断_新規",
        "lp_b": "01タイパ_夏の予定優先×働きやすさ_ブランド診断_新規_B",
    },
    {
        "creative": "夏期講習の先行確保",
        "lp_a": "01タイパ_夏期講習の先行確保_ブランド診断_新規",
        "lp_b": "01タイパ_夏期講習の先行確保_ブランド診断_新規_B",
    },
]
ALL_AD_NAMES = [p["lp_a"] for p in PAIRS] + [p["lp_b"] for p in PAIRS]


def get_creds():
    return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)


def find_sheet_name(sheets_service):
    meta = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for s in meta.get("sheets", []):
        if str(s["properties"]["sheetId"]) == SHEET_GID:
            return s["properties"]["title"]
    return None


def query_st(bq_client):
    placeholders = ", ".join([f"@ad_{i}" for i in range(len(ALL_AD_NAMES))])
    sql = f"""
    WITH agg AS (
      SELECT
        ad_name,
        MIN(target_date)              AS first_date,
        MAX(target_date)              AS last_date,
        SUM(spend)                    AS spend,
        SUM(complete_registration)    AS cv,
        SUM(link_clicks)             AS link_clicks,
        SUM(impressions)             AS impressions
      FROM `bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report`
      WHERE ad_name IN ({placeholders})
      GROUP BY ad_name
    )
    SELECT
      ad_name, first_date, last_date, spend, cv, link_clicks, impressions,
      SAFE_DIVIDE(spend, cv)                 AS cpa,
      SAFE_DIVIDE(cv, link_clicks)           AS cvr,
      SAFE_DIVIDE(link_clicks, impressions)  AS ctr
    FROM agg
    ORDER BY ad_name
    """
    params = [bigquery.ScalarQueryParameter(f"ad_{i}", "STRING", n) for i, n in enumerate(ALL_AD_NAMES)]
    return bq_client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).to_dataframe()


def fmt(v, mode="pct"):
    try:
        f = float(v)
        if mode == "pct":
            return f"{f*100:.2f}%"
        elif mode == "yen":
            return f"¥{f:,.0f}"
        elif mode == "int":
            return f"{int(f):,}"
    except:
        pass
    return "-"


def safe_diff(a, b):
    """(b-a)/a の変化率"""
    try:
        fa, fb = float(a), float(b)
        if fa == 0:
            return "-"
        diff = (fb - fa) / fa * 100
        return f"{diff:+.1f}%"
    except:
        return "-"


def winner(a, b, higher_is_better=True):
    try:
        fa, fb = float(a), float(b)
        if fa == fb:
            return "同等"
        if higher_is_better:
            return "LP-A 優位" if fa > fb else "LP-B 優位"
        else:
            return "LP-A 優位" if fa < fb else "LP-B 優位"
    except:
        return "-"


def build_sheet_rows(df):
    # ad_name → rowの辞書
    data = {r["ad_name"]: r for _, r in df.iterrows()}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    rows.append([f"LPO ABテスト分析 ブランド診断LP（{now} 更新）"])
    rows.append(["LP-A: ブランド診断LP（既存）　LP-B: 変更後LP"])
    rows.append(["CV定義: complete_registration（LINE登録）/ データソース: ST_meta_rpt"])
    rows.append([""])

    for pair in PAIRS:
        cname = pair["creative"]
        a_name, b_name = pair["lp_a"], pair["lp_b"]
        ra = data.get(a_name)
        rb = data.get(b_name)

        rows.append([f"■ クリエイティブ: {cname}"])
        rows.append(["LP", "広告名", "配信期間", "消化金額", "IMP", "クリック", "CTR", "CV数", "CVR", "CPA"])

        has_a = ra is not None
        has_b = rb is not None

        def make_row(label, r, name, has):
            if not has:
                return [label, name, "データなし", "", "", "", "", "", "", ""]
            period = f"{r['first_date']} ~ {r['last_date']}"
            return [
                label, name, period,
                fmt(r["spend"], "yen"),
                fmt(r["impressions"], "int"),
                fmt(r["link_clicks"], "int"),
                fmt(r["ctr"], "pct"),
                fmt(r["cv"], "int"),
                fmt(r["cvr"], "pct"),
                fmt(r["cpa"], "yen"),
            ]

        rows.append(make_row("LP-A", ra, a_name, has_a))
        rows.append(make_row("LP-B", rb, b_name, has_b))

        # 差分行
        rows.append(["【差分】", "", "",
            (safe_diff(ra["spend"], rb["spend"]) + " (B vs A)") if has_a and has_b else "-",
            "", "",
            (safe_diff(ra["ctr"], rb["ctr"]) + " (B vs A)") if has_a and has_b else "-",
            "",
            (safe_diff(ra["cvr"], rb["cvr"]) + " (B vs A)") if has_a and has_b else "-",
            (safe_diff(ra["cpa"], rb["cpa"]) + " (B vs A)") if has_a and has_b else "-",
        ])

        # 判定
        cvr_a = ra["cvr"] if has_a else None
        cvr_b = rb["cvr"] if has_b else None
        cpa_a = ra["cpa"] if has_a else None
        cpa_b = rb["cpa"] if has_b else None
        rows.append([
            "判定",
            f"CVR: {winner(cvr_a, cvr_b, higher_is_better=True)}",
            f"CPA: {winner(cpa_a, cpa_b, higher_is_better=False)}",
        ])
        rows.append([""])

    rows.append(["＊ spend < ¥10,000 の広告は統計的に不安定（参考値）"])
    rows.append(["＊ 直近40日以内のCVは過小評価の可能性あり（FV登録→面談中央値40日ラグ）"])
    return rows


def main():
    creds = get_creds()
    bq = bigquery.Client(project=PROJECT_ID, credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    sheet_name = find_sheet_name(sheets)
    if not sheet_name:
        print(f"シートGID {SHEET_GID} が見つかりません")
        sys.exit(1)
    print(f"対象シート: 「{sheet_name}」")

    print("BigQueryクエリ実行中...")
    df = query_st(bq)
    print(f"  → {len(df)} 件ヒット")
    for _, r in df.iterrows():
        print(f"    {r['ad_name']}: spend={fmt(r['spend'],'yen')}  cv={fmt(r['cv'],'int')}  cpa={fmt(r['cpa'],'yen')}  cvr={fmt(r['cvr'],'pct')}")

    rows = build_sheet_rows(df)

    # クリアして書き込み
    sheets.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range=f"'{sheet_name}'!A1:Z80"
    ).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": rows}
    ).execute()
    print(f"スプレッドシート「{sheet_name}」に書き込み完了。")


if __name__ == "__main__":
    main()
