"""
ST Meta広告 分析レポート（直近90日）→ Google Doc出力
対象: STの全キャンペーン / spend >= 1万円のクリエイティブ
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery
from googleapiclient.discovery import build

TOKEN_FILE = "/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

bq_client  = bigquery.Client(project="bigquery-jukust", credentials=creds)
docs_svc   = build("docs", "v1", credentials=creds, cache_discovery=False)

BQ_VIEW = "bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report"

# ── BigQuery クエリ（90日 / クリエイティブ別） ──────────────────────
Q_90D = f"""
WITH base AS (
  SELECT
    target_date,
    campaign_name,
    ad_name,
    spend,
    link_clicks,
    complete_registration AS line_cv,
    impressions
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    AND target_date < CURRENT_DATE()
)
, agg AS (
  SELECT
    campaign_name,
    ad_name,
    SUM(spend)       AS spend,
    SUM(link_clicks) AS clicks,
    SUM(line_cv)     AS line_cv,
    SUM(impressions) AS impressions,
    MIN(target_date) AS date_from,
    MAX(target_date) AS date_to,
    SAFE_DIVIDE(SUM(spend), SUM(line_cv))        AS line_cpa,
    SAFE_DIVIDE(SUM(line_cv), SUM(link_clicks))  AS cvr,
    SAFE_DIVIDE(SUM(link_clicks), SUM(impressions)) AS ctr
  FROM base
  GROUP BY campaign_name, ad_name
)
SELECT * FROM agg
WHERE spend >= 10000
ORDER BY spend DESC
"""

Q_CAMPAIGN = f"""
WITH base AS (
  SELECT
    campaign_name,
    spend,
    link_clicks,
    complete_registration AS line_cv,
    impressions
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    AND target_date < CURRENT_DATE()
)
SELECT
  campaign_name,
  SUM(spend)       AS spend,
  SUM(link_clicks) AS clicks,
  SUM(line_cv)     AS line_cv,
  SAFE_DIVIDE(SUM(spend), SUM(line_cv)) AS line_cpa,
  SAFE_DIVIDE(SUM(line_cv), SUM(link_clicks)) AS cvr,
  SAFE_DIVIDE(SUM(link_clicks), SUM(impressions)) AS ctr
FROM base
GROUP BY campaign_name
ORDER BY spend DESC
"""

print("BigQueryからデータ取得中（直近90日）...")
ad_rows   = list(bq_client.query(Q_90D).result())
camp_rows = list(bq_client.query(Q_CAMPAIGN).result())

total_spend = sum(r['spend'] or 0 for r in ad_rows)
total_cv    = sum(r['line_cv'] or 0 for r in ad_rows)
print(f"  広告別: {len(ad_rows)}件（spend >= 1万円）")
print(f"  キャンペーン別: {len(camp_rows)}件")
print(f"  合計消化: ¥{total_spend:,.0f} / LINE_CV: {total_cv:.0f}件")

# ── レポート本文の構築 ─────────────────────────────────────────────
def fmt(v, kind='yen'):
    if v is None: return "—"
    if kind == 'yen':  return f"¥{v:,.0f}"
    if kind == 'pct':  return f"{v*100:.2f}%"
    return str(v)

lines = []

lines.append("ST Meta広告 分析レポート（直近90日）\n")
lines.append("作成: 2026-09-05  |  データ期間: 直近90日（BQ値・ビュースルーCV含む可能性あり）\n")
lines.append("※ 本レポートのCV値はBigQueryによる集計値。管理画面確認が推奨（ビュースルーCV混在の可能性）。\n")
lines.append("\n")

# ── セクション0: エグゼクティブサマリー ──
lines.append("【0. サマリー】\n")
lines.append(f"直近90日の合計消化（spend >= 1万円の広告のみ）: ¥{total_spend:,.0f}\n")
lines.append(f"LINE登録CV合計（BQ）: {total_cv:.0f}件\n")
cpa_all = total_spend / total_cv if total_cv else 0
lines.append(f"全体LINE_CPA: {fmt(cpa_all)} \n")
lines.append("\n")

# ── セクション1: キャンペーン別サマリー ──
lines.append("【1. キャンペーン別サマリー（直近90日）】\n")
lines.append(f"{'キャンペーン名':<60}  {'消化':>10}  {'LINE_CV':>7}  {'LINE_CPA':>10}  {'CVR':>6}  {'CTR':>6}\n")
lines.append("─" * 110 + "\n")
for r in camp_rows:
    name = (r['campaign_name'] or '')[:58]
    lines.append(
        f"{name:<60}  {fmt(r['spend']):>10}  {(r['line_cv'] or 0):>7.0f}  "
        f"{fmt(r['line_cpa']):>10}  {fmt(r['cvr'],'pct'):>6}  {fmt(r['ctr'],'pct'):>6}\n"
    )
lines.append("\n")

# ── セクション2: 上位クリエイティブ TOP10 ──
lines.append("【2. 上位クリエイティブ（LINE_CPA順 / spend >= 1万円）TOP10】\n")
sorted_by_cpa = sorted(
    [r for r in ad_rows if r['line_cv'] and r['line_cv'] > 0],
    key=lambda r: r['line_cpa'] or 999999
)[:10]

lines.append(f"{'広告名':<60}  {'消化':>10}  {'CV':>5}  {'LINE_CPA':>10}  {'CVR':>6}\n")
lines.append("─" * 100 + "\n")
for r in sorted_by_cpa:
    name = (r['ad_name'] or '')[:58]
    lines.append(
        f"{name:<60}  {fmt(r['spend']):>10}  {(r['line_cv'] or 0):>5.0f}  "
        f"{fmt(r['line_cpa']):>10}  {fmt(r['cvr'],'pct'):>6}\n"
    )
lines.append("\n")

# ── セクション3: 不振クリエイティブ（spend >= 1万円 / CV 0件） ──
lines.append("【3. 不振クリエイティブ（spend >= 1万円 / CV 0件）】\n")
zero_cv = sorted(
    [r for r in ad_rows if (r['line_cv'] or 0) == 0],
    key=lambda r: r['spend'], reverse=True
)

lines.append(f"{'広告名':<60}  {'消化':>10}  {'CTR':>6}  {'期間'}\n")
lines.append("─" * 90 + "\n")
for r in zero_cv:
    name = (r['ad_name'] or '')[:58]
    period = f"{r['date_from']}〜{r['date_to']}"
    lines.append(f"{name:<60}  {fmt(r['spend']):>10}  {fmt(r['ctr'],'pct'):>6}  {period}\n")
lines.append("\n")

# ── セクション4: インサイト・推奨アクション ──
lines.append("【4. インサイト & 推奨アクション】\n")
lines.append("\n")
lines.append("■ MTGの決定事項（2026-09-02）\n")
lines.append("  ・データ分析は管理画面を参照（BigQueryのCV＝ビュースルー混在のため参考値扱い）\n")
lines.append("  ・競合分析を深めてLP改善を推進\n")
lines.append("  ・1シーズン各キャンペーンに5個のクリエイティブを用意する方針\n")
lines.append("\n")
lines.append("■ 勝ちパターンの傾向\n")
lines.append("  ・「単願訴求 × ブランド診断CTA」の組み合わせが最もCPAが良い\n")
lines.append("  ・静止画でもCVが出る（02単願_静止画8月CR1v2 は 8月W4でCV 6件・CPA ¥12,310）\n")
lines.append("  ・診断系CTAはLP遷移型より心理的ハードルが低く、CVRが高い傾向\n")
lines.append("  ・「タイパ」「単願」など働き方を具体的に定義する訴求が刺さる\n")
lines.append("\n")
lines.append("■ 不振パターンの傾向\n")
lines.append("  ・複数訴求を1本に詰め込むとメッセージが散漫になりCV 0になりやすい\n")
lines.append("  ・強いフック（金欠・ピンチ）でクリックを取っても LP でCV に至らないケースが多い\n")
lines.append("  ・顕在層(LINE)キャンペーンは 8月W4でCPA ¥59,389 → 疲弊の可能性\n")
lines.append("\n")
lines.append("■ 優先アクション（優先度順）\n")
lines.append("\n")
lines.append("① 【即時】不振クリエイティブの停止（spend >= 1万円 / CV 0件）\n")
lines.append("   → 上記【3】の広告を管理画面で停止し、予算を勝ちクリエイティブに集中\n")
lines.append("\n")
lines.append("② 【今週中】勝ちクリエイティブの横展開\n")
lines.append("   → 02単願_静止画8月CR1v2 をベースに、タイパ訴求・併願訴求バージョンを作成\n")
lines.append("   → 1シーズン5本目安に向けて各キャンペーンでクリエイティブを補充\n")
lines.append("\n")
lines.append("③ 【今月中】顕在層キャンペーンの見直し\n")
lines.append("   → フリークエンシーとオーディエンス重複を確認\n")
lines.append("   → クリエイティブを勝ちパターン（02単願 × ブランド診断）に差し替え\n")
lines.append("\n")
lines.append("④ 【次期LP検証】広告訴求とFVの整合性改善\n")
lines.append("   → B2分析（別ドキュメント参照）でも確認済み: 「夏」「働きやすさ」がLPに存在しない\n")
lines.append("   → FVバリアント作成（シフト週1〜OK / 夏休みだけOK）を next LP として優先\n")
lines.append("\n")
lines.append("■ 計測環境の改善（MTG合意）\n")
lines.append("  ・管理画面のアトリビューション表示を「28日クリック後＋1日視聴後」に変更\n")
lines.append("  ・custom_cv_2（応募CV）のバグ修正: 現在LINE登録CVと同値になっている（要調査）\n")
lines.append("  ・BQとの乖離確認: 定期的に管理画面の実数と照合すること\n")
lines.append("\n")
lines.append("■ 引き継ぎ向け補足（岩崎さんへの説明ポイント）\n")
lines.append("  ・BQ値はビュースルーCV含む → 管理画面の数値が正確\n")
lines.append("  ・直近40日以内のCV数値は過小評価（応募タイムラグ中央値40日）\n")
lines.append("  ・クリエイティブ評価は spend >= 1万円 のみを対象にする\n")
lines.append("  ・kpi-report スキルで毎週自動生成可能（python3 scripts/kpi/kpi_report_st.py 期間）\n")

full_text = "".join(lines)

# ── Google Doc 作成 ──────────────────────────────────────────────
print("\nGoogle Docを作成中...")
doc = docs_svc.documents().create(body={
    "title": "ST Meta広告 分析レポート（直近90日・2026-09-05）"
}).execute()
DOC_ID = doc["documentId"]
print(f"ドキュメント作成: https://docs.google.com/document/d/{DOC_ID}/edit")

docs_svc.documents().batchUpdate(
    documentId=DOC_ID,
    body={"requests": [
        {"insertText": {"location": {"index": 1}, "text": full_text}}
    ]},
).execute()
print("テキスト挿入完了")
time.sleep(1)

title_end = full_text.index('\n') + 1
docs_svc.documents().batchUpdate(
    documentId=DOC_ID,
    body={"requests": [
        {
            "updateParagraphStyle": {
                "range": {"startIndex": 1, "endIndex": title_end},
                "paragraphStyle": {"namedStyleType": "HEADING_1"},
                "fields": "namedStyleType",
            }
        },
        {
            "updateTextStyle": {
                "range": {"startIndex": 1, "endIndex": len(full_text)},
                "textStyle": {"weightedFontFamily": {"fontFamily": "Noto Sans JP"}},
                "fields": "weightedFontFamily",
            }
        },
    ]},
).execute()
print("スタイル適用完了")

url = f"https://docs.google.com/document/d/{DOC_ID}/edit"
print(f"\n完成URL: {url}")
