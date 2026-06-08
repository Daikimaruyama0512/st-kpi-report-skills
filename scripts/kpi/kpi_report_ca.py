# CA KPIレポート生成スクリプト
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth google-api-python-client google-generativeai python-dotenv
#
# 使い方:
#   adset名一覧を確認（初回）:
#     python3 scripts/kpi_report_ca.py --list-adsets
#
#   指定期間でレポート生成:
#     python3 scripts/kpi_report_ca.py 2026/05/01-2026/05/07
#
#   スプシにも書き込む（SPREADSHEET_ID 設定後）:
#     python3 scripts/kpi_report_ca.py 2026/05/01-2026/05/07 --write

import sys
import io
import os
import json
from datetime import date, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

# ============================================================
# ★ ここをカスタマイズ
# ============================================================

# adset_name に含まれるキーワードで分類する
# BQ確認後（--list-adsets）に実際のキーワードに更新すること
ADSET_GROUPS = {
    '顕在層': ['顕在'],
    '潜在層（LINE）': ['潜在', 'LINE'],
    # 例: 'Google': ['Google', 'GDN'],
}

# CPA 評価閾値（面談単価）
# purchase = エージェント申込CV（FV登録後の面談申込）
CPA_THRESHOLDS = {
    'good': 50000,   # ✅ 良好
    'ok':   90000,   # △ 要観察（90000超は ❌）
}

# スプレッドシート設定（CA_KPI報告シートが用意されたらIDを記入）
SPREADSHEET_ID = ''
SHEET_NAME = 'CA_KPI報告'

# ============================================================
# 認証設定
# ============================================================
TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
ENV_FILE   = r"/Users/119322/Desktop/claude-code-template_af/.env"
PROJECT_ID = "bigquery-jukust"
BQ_VIEW    = "bigquery-jukust.CA_meta_rpt.v_CA_meta_ads_daily_report_with_scenario"

SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/spreadsheets',
]

# ============================================================
# .env からGemini APIキー読み込み
# ============================================================
def load_env(env_file):
    env = {}
    if not os.path.exists(env_file):
        return env
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

env = load_env(ENV_FILE)
GEMINI_API_KEY = env.get('GEMINI_API_KEY', '')

# ============================================================
# 引数パース
# ============================================================
args = sys.argv[1:]
list_adsets_mode = '--list-adsets' in args
write_mode = '--write' in args
date_arg = None

for a in args:
    if '-' in a and '/' in a and '--' not in a:
        date_arg = a

def parse_date_arg(s):
    """'2026/05/01-2026/05/07' → (start_date, end_date)"""
    parts = s.split('-')
    if len(parts) == 2:
        try:
            start = datetime.strptime(parts[0].strip(), '%Y/%m/%d').date()
            end   = datetime.strptime(parts[1].strip(), '%Y/%m/%d').date()
            return start, end
        except ValueError:
            pass
    # 3つにsplitされる場合（2026-05-01-2026-05-07）も対応
    return None, None

if not list_adsets_mode and not date_arg:
    print("使い方:")
    print("  adset名一覧を確認: python3 scripts/kpi_report_ca.py --list-adsets")
    print("  レポート生成:       python3 scripts/kpi_report_ca.py 2026/05/01-2026/05/07")
    print("  スプシ書き込みも:   python3 scripts/kpi_report_ca.py 2026/05/01-2026/05/07 --write")
    sys.exit(0)

if date_arg:
    start_date, end_date = parse_date_arg(date_arg)
    if not start_date:
        print(f"日付フォーマットエラー: {date_arg}")
        print("正しい形式: 2026/05/01-2026/05/07")
        sys.exit(1)
    print(f"対象期間: {start_date} 〜 {end_date}")
else:
    start_date = end_date = None

# ============================================================
# BigQuery 認証
# ============================================================
print("\n=== BigQuery認証 ===")
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
client = bigquery.Client(project=PROJECT_ID, credentials=creds)
print("  認証OK")

# ============================================================
# ヘルパー関数
# ============================================================
def safe_float(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return f if f != 0.0 else default
    except (ValueError, TypeError):
        return default

def fmt_num(val, prefix='¥', suffix='', decimal=0):
    if val is None:
        return 'N/A'
    if decimal == 0:
        return f"{prefix}{int(val):,}{suffix}"
    return f"{prefix}{val:,.{decimal}f}{suffix}"

def fmt_pct(val):
    if val is None:
        return 'N/A'
    return f"{float(val):.2f}%"

def cpa_mark(cpa):
    if cpa is None:
        return '-'
    if cpa <= CPA_THRESHOLDS['good']:
        return 'OK'
    if cpa <= CPA_THRESHOLDS['ok']:
        return 'CHECK'
    return 'NG'

# ============================================================
# STEP 2A: --list-adsets モード（初回キーワード確認用）
# ============================================================
if list_adsets_mode:
    print("\n=== adset名・campaign名一覧（直近90日・spend合計降順）===")
    list_query = f"""
WITH agg AS (
  SELECT
    adset_name,
    campaign_name,
    SUM(spend) AS spend
  FROM `{BQ_VIEW}`
  WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
  GROUP BY adset_name, campaign_name
)
SELECT adset_name, campaign_name, spend
FROM agg
ORDER BY spend DESC
"""
    rows = list(client.query(list_query).result())
    print(f"\n{'adset_name':<50} {'campaign_name':<40} {'spend':>12}")
    print('-' * 110)
    for r in rows:
        adset = str(r['adset_name'] or '')[:48]
        camp  = str(r['campaign_name'] or '')[:38]
        spend = int(r['spend']) if r['spend'] else 0
        print(f"{adset:<50} {camp:<40} {spend:>12,}")
    print(f"\n合計 {len(rows)} 件")
    print("\nこの一覧を参考に、スクリプト冒頭の ADSET_GROUPS にキーワードを設定してください。")
    sys.exit(0)

# ============================================================
# STEP 2B: 指定期間のデータ取得
# ============================================================
print(f"\n=== STEP 2B: BigQuery データ取得（{start_date} 〜 {end_date}）===")

# 広告別集計（spend >= 10000 のみ）
ad_query = f"""
WITH base AS (
  SELECT
    ad_name,
    adset_name,
    campaign_name,
    ANY_VALUE(scenario_text) AS scenario_text,
    SUM(spend)        AS spend,
    SUM(purchase)     AS cv,
    SUM(link_clicks)  AS link_clicks,
    SUM(impressions)  AS impressions
  FROM `{BQ_VIEW}`
  WHERE date BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
  GROUP BY ad_name, adset_name, campaign_name
),
filtered AS (
  SELECT
    ad_name, adset_name, campaign_name, scenario_text,
    spend, cv, link_clicks, impressions,
    SAFE_DIVIDE(spend, cv)                               AS cpa,
    SAFE_DIVIDE(cv, link_clicks) * 100                   AS cvr,
    SAFE_DIVIDE(link_clicks, impressions) * 100          AS ctr,
    SAFE_DIVIDE(spend, NULLIF(impressions, 0)) * 1000    AS cpm
  FROM base
  WHERE spend >= 10000
)
SELECT * FROM filtered ORDER BY cpa ASC NULLS LAST
"""

ad_rows = [dict(r.items()) for r in client.query(ad_query).result()]
print(f"  広告別データ取得: {len(ad_rows)} 件（spend >= 1万円）")

# 全体集計
total_query = f"""
WITH base AS (
  SELECT
    SUM(spend)       AS spend,
    SUM(purchase)    AS cv,
    SUM(link_clicks) AS link_clicks,
    SUM(impressions) AS impressions
  FROM `{BQ_VIEW}`
  WHERE date BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
)
SELECT
  spend, cv, link_clicks, impressions,
  SAFE_DIVIDE(spend, cv)                            AS cpa,
  SAFE_DIVIDE(cv, link_clicks) * 100                AS cvr,
  SAFE_DIVIDE(link_clicks, impressions) * 100       AS ctr,
  SAFE_DIVIDE(spend, NULLIF(impressions, 0)) * 1000 AS cpm
FROM base
"""
total_rows = list(client.query(total_query).result())
total = dict(total_rows[0].items()) if total_rows else {}
print(f"  全体: spend={fmt_num(total.get('spend'))} / CV={total.get('cv')} / CPA={fmt_num(total.get('cpa'))}")

# ============================================================
# STEP 3: adset_name キーワードで分類 × KPI集計
# ============================================================
print("\n=== STEP 3: adset_nameキーワードで分類 ===")

def classify_adset(adset_name):
    """adset_nameを ADSET_GROUPS のキーワードに照らして分類する"""
    if not adset_name:
        return 'その他'
    for group_name, keywords in ADSET_GROUPS.items():
        for kw in keywords:
            if kw in adset_name:
                return group_name
    return 'その他'

# グループ別集計
group_totals = {}
for r in ad_rows:
    group = classify_adset(str(r.get('adset_name') or ''))
    if group not in group_totals:
        group_totals[group] = {'spend': 0, 'cv': 0, 'link_clicks': 0, 'impressions': 0, 'ads': []}
    g = group_totals[group]
    g['spend']       += float(r.get('spend') or 0)
    g['cv']          += int(r.get('cv') or 0)
    g['link_clicks'] += int(r.get('link_clicks') or 0)
    g['impressions'] += int(r.get('impressions') or 0)
    g['ads'].append(r)

# 集計値からKPI算出
for gname, g in group_totals.items():
    g['cpa'] = g['spend'] / g['cv'] if g['cv'] > 0 else None
    g['cvr'] = g['cv'] / g['link_clicks'] * 100 if g['link_clicks'] > 0 else None
    g['ctr'] = g['link_clicks'] / g['impressions'] * 100 if g['impressions'] > 0 else None
    g['cpa_mark'] = cpa_mark(g['cpa'])
    print(f"  [{gname}] spend={fmt_num(g['spend'])} / CV={g['cv']} / CPA={fmt_num(g['cpa'])} {g['cpa_mark']}")

print(f"  [その他] 広告数={len(group_totals.get('その他', {}).get('ads', []))}")

# ============================================================
# STEP 4: Gemini AI でテキスト生成
# ============================================================
print("\n=== STEP 4: Gemini AI テキスト生成 ===")

gemini_texts = {
    'jisho':   '[Gemini未設定]',
    'youin':   '[Gemini未設定]',
    'shisa':   '[Gemini未設定]',
    'next':    '[Gemini未設定]',
}

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-pro')

        # 集計データのサマリーを作成
        group_summary_lines = []
        for gname, g in group_totals.items():
            if gname == 'その他':
                continue
            group_summary_lines.append(
                f"- {gname}: spend={fmt_num(g['spend'])} / CV={g['cv']} / CPA={fmt_num(g['cpa'])} {g['cpa_mark']}"
                f" / CTR={fmt_pct(g['ctr'])} / CVR={fmt_pct(g['cvr'])}"
            )

        top_ads = ad_rows[:5]
        top_ads_lines = [
            f"  {i+1}. 「{str(r['ad_name'])[:40]}」spend={fmt_num(r['spend'])} CV={r['cv']} CPA={fmt_num(r.get('cpa'))}"
            for i, r in enumerate(top_ads)
        ]

        prompt = f"""
あなたはMeta広告運用の専門家です。以下のCA（塾講師ステーションキャリア）のKPIデータを分析して、4セクションのレポートを日本語で生成してください。

## 対象期間
{start_date} 〜 {end_date}

## 全体KPI
- 広告費合計: {fmt_num(total.get('spend'))}
- エージェント申込CV合計: {total.get('cv')}件
- 全体CPA: {fmt_num(total.get('cpa'))}
- 全体CTR: {fmt_pct(total.get('ctr'))}
- 全体CVR: {fmt_pct(total.get('cvr'))}

## 分類別KPI（adset_nameキーワード分類）
{chr(10).join(group_summary_lines) if group_summary_lines else '分類キーワード未設定（ADSET_GROUPSを設定してください）'}

## 上位クリエイティブ（CPA順）
{chr(10).join(top_ads_lines)}

## 事業背景
- CAはエージェント型転職支援サービス（塾講師ステーションキャリア）
- 最重要KPI: エージェント申込数（年間700件目標）
- Meta FV登録→面談申込タイムラグ: 中央値40日
- 直近40日以内のCV数は過小評価の可能性がある
- 年間広告費: 約3,290万円

## 出力形式
以下の4セクションを、各セクションの見出し（★ 事象、★ 要因仮説、★ 示唆、★ ネクスト）の後に内容を記載してください。
仮説・推測には証拠強度（★★★データで直接示せる事実/★★間接的推測/★論理的推定）を付けてください。

★ 事象
（データが示す今期間の状況を具体的な数値を引用して記述。200字以内）

★ 要因仮説
（なぜその数値になったか。証拠強度付き。3点以内）

★ 示唆
▼WHO（データが示すターゲット層の状態・行動パターン）
▼WHAT（今の層に刺さる提供価値・メッセージ軸）
▼HOW（クリエイティブ方向性・CTA選択・予算配分）

★ ネクスト
（優先施策と理由。証拠強度付き。3点以内）
"""

        response = model.generate_content(prompt)
        raw_text = response.text

        # セクションを分割
        def extract_section(text, header):
            import re
            pattern = rf'★\s*{re.escape(header)}\s*\n(.*?)(?=★\s|\Z)'
            m = re.search(pattern, text, re.DOTALL)
            return m.group(1).strip() if m else '[取得失敗]'

        gemini_texts['jisho']  = extract_section(raw_text, '事象')
        gemini_texts['youin']  = extract_section(raw_text, '要因仮説')
        gemini_texts['shisa']  = extract_section(raw_text, '示唆')
        gemini_texts['next']   = extract_section(raw_text, 'ネクスト')
        print("  Gemini AIテキスト生成完了")

    except ImportError:
        print("  [スキップ] google-generativeai 未インストール")
        print("    → pip install google-generativeai でインストールしてください")
    except Exception as e:
        print(f"  [エラー] Gemini API エラー: {e}")
else:
    print("  [スキップ] GEMINI_API_KEY が .env に未設定")
    print("    → .env に GEMINI_API_KEY=AIza... を追加してください")

# ============================================================
# STEP 5: コンソール出力
# ============================================================

period_str = f"{start_date} 〜 {end_date}"
days = (end_date - start_date).days + 1

report = f"""
================================================================
  CA Meta広告 KPIレポート  {period_str}（{days}日間）
================================================================

【全体KPI】
広告費合計 : {fmt_num(total.get('spend'))}
申込CV合計 : {total.get('cv')}件
全体CPA    : {fmt_num(total.get('cpa'))}
全体CTR    : {fmt_pct(total.get('ctr'))}
全体CVR    : {fmt_pct(total.get('cvr'))}

※ 直近40日以内のCV数は過小評価の可能性あり（FV登録→面談申込タイムラグ中央値40日）

---
【分類別KPI】（adset_nameキーワード分類 / spend >= 1万円のみ）

{'分類名':<20} {'spend':>12} {'CV':>6} {'CPA':>12} {'評価':>6} {'CTR':>8} {'CVR':>8}
{'-'*80}"""

for gname, g in group_totals.items():
    if gname == 'その他':
        continue
    report += (
        f"\n{gname:<20} {fmt_num(g['spend']):>12} {g['cv']:>6}"
        f" {fmt_num(g['cpa']):>12} {g['cpa_mark']:>6}"
        f" {fmt_pct(g['ctr']):>8} {fmt_pct(g['cvr']):>8}"
    )

other = group_totals.get('その他', {})
if other:
    report += (
        f"\n{'その他':<20} {fmt_num(other.get('spend')):>12} {other.get('cv', 0):>6}"
        f" {fmt_num(other.get('cpa')):>12} {'-':>6}"
        f" {fmt_pct(other.get('ctr')):>8} {fmt_pct(other.get('cvr')):>8}"
    )

report += f"""

評価凡例: OK=✅ 良好（CPA <= {CPA_THRESHOLDS['good']:,}円）/ CHECK=△ 要観察（<= {CPA_THRESHOLDS['ok']:,}円）/ NG=❌ 要見直し

---
【上位クリエイティブ（CPA順 / spend >= 1万円）】

{'広告名':<45} {'spend':>10} {'CV':>5} {'CPA':>12} {'CTR':>8} {'CVR':>8}
{'-'*95}"""

for r in ad_rows[:15]:
    ad = str(r.get('ad_name') or '')[:43]
    report += (
        f"\n{ad:<45} {fmt_num(r.get('spend')):>10} {int(r.get('cv') or 0):>5}"
        f" {fmt_num(r.get('cpa')):>12} {fmt_pct(r.get('ctr')):>8} {fmt_pct(r.get('cvr')):>8}"
    )

report += f"""

---
★ 事象

{gemini_texts['jisho']}

---
★ 要因仮説

{gemini_texts['youin']}

---
★ 示唆

{gemini_texts['shisa']}

---
★ ネクスト

{gemini_texts['next']}

================================================================
"""

print(report)

# ============================================================
# JSON 保存
# ============================================================
output_file = r"/Users/119322/Desktop/claude-code-template_af/scripts/kpi_report_ca_data.json"
save_data = {
    'period_start': start_date.isoformat(),
    'period_end':   end_date.isoformat(),
    'total': {
        'spend':  float(total.get('spend') or 0),
        'cv':     int(total.get('cv') or 0),
        'cpa':    float(total.get('cpa') or 0) if total.get('cpa') else None,
        'ctr':    float(total.get('ctr') or 0) if total.get('ctr') else None,
        'cvr':    float(total.get('cvr') or 0) if total.get('cvr') else None,
    },
    'group_totals': {
        gname: {
            'spend':  g['spend'],
            'cv':     g['cv'],
            'cpa':    g['cpa'],
            'ctr':    g['ctr'],
            'cvr':    g['cvr'],
            'cpa_mark': g['cpa_mark'],
        }
        for gname, g in group_totals.items()
    },
    'ad_rows': [
        {
            'ad_name':     str(r.get('ad_name') or ''),
            'adset_name':  str(r.get('adset_name') or ''),
            'group':       classify_adset(str(r.get('adset_name') or '')),
            'spend':       float(r.get('spend') or 0),
            'cv':          int(r.get('cv') or 0),
            'cpa':         float(r.get('cpa')) if r.get('cpa') else None,
            'ctr':         float(r.get('ctr')) if r.get('ctr') else None,
            'cvr':         float(r.get('cvr')) if r.get('cvr') else None,
            'scenario':    str(r.get('scenario_text') or '')[:100],
        }
        for r in ad_rows
    ],
    'gemini_texts': gemini_texts,
}

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(save_data, f, ensure_ascii=False, indent=2)
print(f"生データを {output_file} に保存しました。")

# ============================================================
# STEP 6: スプシ書き込み（--write フラグ + SPREADSHEET_ID 設定時のみ）
# ============================================================
if write_mode:
    if not SPREADSHEET_ID:
        print("\n[スキップ] SPREADSHEET_ID が未設定です。")
        print("  スクリプト冒頭の SPREADSHEET_ID にCA_KPI報告シートのIDを記入してください。")
    else:
        print(f"\nスプレッドシートに書き込みます（{SPREADSHEET_ID}）")
        from googleapiclient.discovery import build

        svc = build('sheets', 'v4', credentials=creds)

        # ヘッダー行
        header = [['広告名', 'adset分類', 'spend（円）', 'CV', 'CPA（円）', 'CPA評価', 'CTR(%)', 'CVR(%)','集計期間']]
        ad_sheet_rows = header + [
            [
                str(r['ad_name']),
                classify_adset(str(r.get('adset_name') or '')),
                int(r['spend']),
                int(r['cv']),
                int(r['cpa']) if r['cpa'] else 'N/A',
                cpa_mark(r.get('cpa')),
                round(float(r['ctr']), 2) if r.get('ctr') else 'N/A',
                round(float(r['cvr']), 2) if r.get('cvr') else 'N/A',
                f"{start_date} 〜 {end_date}",
            ]
            for r in ad_rows
        ]

        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!A1",
            valueInputOption='USER_ENTERED',
            body={'values': ad_sheet_rows}
        ).execute()
        print(f"  書き込み完了（{len(ad_rows)}行）: {SHEET_NAME}")
else:
    print("\nスプシ書き込みを実行するには: python3 scripts/kpi_report_ca.py " + date_arg + " --write")
