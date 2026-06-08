# ST KPIレポート生成スクリプト v3（期間引数・Gemini AI・adset分類対応版）
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth google-api-python-client google-generativeai python-dotenv
#
# 使い方:
#   adset名一覧を確認（初回）:
#     python3 scripts/kpi_report_st.py --list-adsets
#
#   指定期間でレポート生成:
#     python3 scripts/kpi_report_st.py 2026/05/01-2026/05/07
#
#   スプシにも書き込む:
#     python3 scripts/kpi_report_st.py 2026/05/01-2026/05/07 --write

import sys
import io
import os
import json
import re
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

# ============================================================
# ★ ここをカスタマイズ
# ============================================================

# adset_name に含まれるキーワードで分類する
# --list-adsets で実際のadset名を確認してからキーワードを設定すること
ADSET_GROUPS = {
    '顕在層': ['顕在'],
    '潜在層': ['潜在'],
    # 例: 'LINE配信': ['LINE'],
}

# 応募CPA評価閾値（custom_cv_2 = 応募CV）
CPA_THRESHOLDS = {
    'good': 20000,   # OK  良好
    'ok':   30000,   # CHECK 要観察（30000超は NG）
}

# CTA判定ロジック（ad_nameのサブストリングマッチ）
CTA_GROUPS = {
    'ペルソナLP':   ['ペルソナLP'],
    '塾ブランド診断': ['ブランド診断'],
    '気軽に診断':   ['気軽に診断'],
    '新1年生':      ['新1年生'],
    'SNS ORG':      ['App_'],
}

# スプシ設定（ST_KPI報告シート）
KPI_SHEET_ID  = '1xXeCl4Xbkxz-w_jT49TmA3-voruL2cTbF1f308hZ5vQ'
ST_KPI_SHEET  = 'ST_KPI報告'
ST_KPI_SHEET_V2 = 'ST_KPI報告_v2'   # create_kpi_tab_v2.py で作成したタブ
COPY_SHEET    = 'KPI報告 のコピー'
INPUT_TAB     = '入力'

# スプシ設定（新規独立KPI報告シート / BQ版 / create_kpi_report_standalone.py で作成）
NEW_KPI_SHEET_ID   = '1paEH07JHjoMaAEi29Sa-_kzzLxGwzWFNlR1EyRCsjv8'
NEW_KPI_TAB        = 'KPI報告'

# ============================================================
# 認証設定
# ============================================================
_HERE      = os.path.dirname(os.path.abspath(__file__))
_ROOT      = os.path.dirname(_HERE)  # プロジェクトルート
TOKEN_FILE = os.path.join(_ROOT, "secrets", "token.json")
ENV_FILE   = os.path.join(_ROOT, ".env")
PROJECT_ID = "bigquery-jukust"
BQ_VIEW    = "bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report"

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
write_mode      = '--write'      in args
v2_mode         = '--v2'         in args  # ST_KPI報告_v2 タブに書き込む（集計さん構造）
new_sheet_mode  = '--new-sheet'  in args  # 新独立KPIシート（BQ版）に書き込む
date_arg = None

for a in args:
    if '/' in a and '--' not in a:
        date_arg = a

def parse_date_arg(s):
    """'2026/05/01-2026/05/07' → (start_date, end_date)"""
    parts = s.split('-', 1)
    if len(parts) == 2:
        try:
            start = datetime.strptime(parts[0].strip(), '%Y/%m/%d').date()
            end   = datetime.strptime(parts[1].strip(), '%Y/%m/%d').date()
            return start, end
        except ValueError:
            pass
    return None, None

if not list_adsets_mode and not date_arg:
    print("使い方:")
    print("  adset名一覧を確認: python3 scripts/kpi_report_st.py --list-adsets")
    print("  レポート生成:       python3 scripts/kpi_report_st.py 2026/05/01-2026/05/07")
    print("  スプシ書き込み:     python3 scripts/kpi_report_st.py 2026/05/01-2026/05/07 --write")
    print("  v2タブに書き込み:   python3 scripts/kpi_report_st.py 2026/05/01-2026/05/07 --write --v2")
    sys.exit(0)

if date_arg:
    start_date, end_date = parse_date_arg(date_arg)
    if not start_date:
        print(f"日付フォーマットエラー: {date_arg}")
        print("正しい形式: 2026/05/01-2026/05/07")
        sys.exit(1)
    # 週ラベルは開始日から計算
    week_of_month = (start_date.day - 1) // 7 + 1
    week_label  = f"{start_date.month}月W{week_of_month}"
    month_str   = f"{start_date.month}月"
    cumul_label = f"{month_str}累積"
    print(f"対象期間: {start_date} 〜 {end_date}（{week_label}）")
else:
    start_date = end_date = None
    week_label = month_str = cumul_label = None

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

def classify_adset(adset_name):
    if not adset_name:
        return 'その他'
    for group_name, keywords in ADSET_GROUPS.items():
        for kw in keywords:
            if kw in str(adset_name):
                return group_name
    return 'その他'

def classify_cta(ad_name):
    if not ad_name:
        return 'その他'
    for cta_name, keywords in CTA_GROUPS.items():
        for kw in keywords:
            if kw in str(ad_name):
                return cta_name
    return 'その他'

# ============================================================
# STEP 2A: --list-adsets モード
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
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
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
    ANY_VALUE(scenario) AS scenario,
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS cv,
    COALESCE(SUM(custom_cv_2), 0) AS obo_cv,
    SUM(link_clicks)           AS link_clicks,
    SUM(impressions)           AS impressions
  FROM `{BQ_VIEW}`
  WHERE target_date BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
  GROUP BY ad_name, adset_name, campaign_name
),
filtered AS (
  SELECT
    ad_name, adset_name, campaign_name, scenario,
    spend, cv, obo_cv, link_clicks, impressions,
    SAFE_DIVIDE(spend, cv)                              AS cpa,
    SAFE_DIVIDE(cv, link_clicks) * 100                  AS cvr,
    SAFE_DIVIDE(link_clicks, impressions) * 100         AS ctr,
    SAFE_DIVIDE(spend, NULLIF(impressions, 0)) * 1000   AS cpm,
    SAFE_DIVIDE(spend, obo_cv)                          AS obo_cpa
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
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS cv,
    COALESCE(SUM(custom_cv_2), 0) AS obo_cv,
    SUM(link_clicks)           AS link_clicks,
    SUM(impressions)           AS impressions
  FROM `{BQ_VIEW}`
  WHERE target_date BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
)
SELECT
  spend, cv, obo_cv, link_clicks, impressions,
  SAFE_DIVIDE(spend, cv)                            AS cpa,
  SAFE_DIVIDE(cv, link_clicks) * 100                AS cvr,
  SAFE_DIVIDE(link_clicks, impressions) * 100       AS ctr,
  SAFE_DIVIDE(spend, NULLIF(impressions, 0)) * 1000 AS cpm,
  SAFE_DIVIDE(spend, obo_cv)                        AS obo_cpa
FROM base
"""
total_rows = list(client.query(total_query).result())
total = dict(total_rows[0].items()) if total_rows else {}

# custom_cv_2 の有効性チェック（LINE登録CVと同値なら応募CVとして使えない）
obo_cv_total = float(total.get('obo_cv') or 0)
line_cv_total = float(total.get('cv') or 0)
use_obo = obo_cv_total > 0 and obo_cv_total != line_cv_total
if not use_obo:
    print("  [注意] custom_cv_2 が 0 または LINE登録CVと同値。応募CVはN/A扱いとします。")

print(f"  全体: spend={fmt_num(total.get('spend'))} / LINE_CV={total.get('cv')} / 応募CV={'N/A' if not use_obo else int(obo_cv_total)}")

# ============================================================
# STEP 3: 分類 × KPI集計
# ============================================================
print("\n=== STEP 3: 分類集計 ===")

# adset_name キーワードで分類
group_totals = {}
for r in ad_rows:
    group = classify_adset(r.get('adset_name'))
    if group not in group_totals:
        group_totals[group] = {'spend': 0, 'cv': 0, 'obo_cv': 0, 'link_clicks': 0, 'impressions': 0, 'ads': []}
    g = group_totals[group]
    g['spend']       += float(r.get('spend') or 0)
    g['cv']          += int(r.get('cv') or 0)
    g['obo_cv']      += float(r.get('obo_cv') or 0)
    g['link_clicks'] += int(r.get('link_clicks') or 0)
    g['impressions'] += int(r.get('impressions') or 0)
    g['ads'].append(r)

for gname, g in group_totals.items():
    g['cpa']      = g['spend'] / g['cv'] if g['cv'] > 0 else None
    g['obo_cpa']  = g['spend'] / g['obo_cv'] if use_obo and g['obo_cv'] > 0 else None
    g['cvr']      = g['cv'] / g['link_clicks'] * 100 if g['link_clicks'] > 0 else None
    g['ctr']      = g['link_clicks'] / g['impressions'] * 100 if g['impressions'] > 0 else None
    g['cpa_mark'] = cpa_mark(g['obo_cpa'])

# CTA別集計
cta_totals = {}
for r in ad_rows:
    cta = classify_cta(r.get('ad_name'))
    if cta not in cta_totals:
        cta_totals[cta] = {'spend': 0, 'cv': 0, 'obo_cv': 0}
    t = cta_totals[cta]
    t['spend']  += float(r.get('spend') or 0)
    t['cv']     += int(r.get('cv') or 0)
    t['obo_cv'] += float(r.get('obo_cv') or 0)

for cta, t in cta_totals.items():
    t['obo_cpa']   = t['spend'] / t['obo_cv'] if use_obo and t['obo_cv'] > 0 else None
    t['cpf']       = t['spend'] / t['cv']      if t['cv'] > 0 else None          # LINE登録CPA
    t['conv_rate'] = t['obo_cv'] / t['cv'] * 100 if use_obo and t['cv'] > 0 else None  # 転換率(%)

print(f"  adset分類: {list(group_totals.keys())}")
print(f"  CTA分類:   {[k for k in cta_totals if k != 'その他']}")

# ============================================================
# STEP 4: 入力タブから予算・目標値取得
# ============================================================
print("\n=== STEP 4: 入力タブ 読み込み ===")
budget = None
target_cv = None

try:
    from googleapiclient.discovery import build
    sheets_service = build('sheets', 'v4', credentials=creds)
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=KPI_SHEET_ID,
        range=f"'{INPUT_TAB}'!A:D",
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    input_rows = result.get('values', [])

    def clean_num(val):
        if val is None or str(val).strip() == '':
            return None
        s = str(val).replace(',', '').replace('¥', '').replace('円', '').replace('%', '').strip()
        try:
            return float(s)
        except ValueError:
            return None

    for row in input_rows[1:]:
        if len(row) >= 1 and str(row[0]).strip().startswith(f"{start_date.month}月"):
            budget    = clean_num(row[1]) if len(row) > 1 else None
            target_cv = clean_num(row[2]) if len(row) > 2 else None
            break
    print(f"  月間予算: {fmt_num(budget)} / LINE登録CV目標: {target_cv}")
except Exception as e:
    print(f"  入力タブ読み込みスキップ: {e}")

# ============================================================
# STEP 5: Gemini AI でテキスト生成
# ============================================================
print("\n=== STEP 5: Gemini AI テキスト生成 ===")

gemini_texts = {
    'sesaku':   '[Gemini未設定]',
    'youin':    '[Gemini未設定]',
    'shisa':    '[Gemini未設定]',
    'next':     '[Gemini未設定]',
    'creative': '[Gemini未設定]',
}

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-pro')

        # 集計サマリー（LINE_CPA・CTR・CVR全列）
        group_lines = []
        for gname, g in group_totals.items():
            if gname == 'その他':
                continue
            line_cpa = g['spend'] / g['cv'] if g['cv'] > 0 else None
            group_lines.append(
                f"- {gname}: spend={fmt_num(g['spend'])} / LINE_CV={g['cv']}"
                f" / LINE_CPA={fmt_num(line_cpa)}"
                f" / CTR={fmt_pct(g['ctr'])} / CVR={fmt_pct(g['cvr'])}"
                f" / 応募CPA={fmt_num(g['obo_cpa'])} {g['cpa_mark']}"
            )

        cta_lines = []
        for cta, t in cta_totals.items():
            if cta == 'その他':
                continue
            cta_lines.append(
                f"- {cta}: spend={fmt_num(t['spend'])} / LINE_CV={t['cv']}"
                f" / LINE_CPA={fmt_num(t['cpf'])}"
                f" / 応募CPA={fmt_num(t['obo_cpa'])}"
            )

        # 上位15件・scenario・CTR・CVRを含める
        top_ads_lines = []
        for i, r in enumerate(ad_rows[:15]):
            scenario_str = str(r.get('scenario') or 'なし')[:25]
            top_ads_lines.append(
                f"  {i+1}. 「{str(r['ad_name'])[:45]}」"
                f" [訴求:{scenario_str}]"
                f" spend={fmt_num(r['spend'])} / LINE_CV={r['cv']}"
                f" / LINE_CPA={fmt_num(r.get('cpa'))}"
                f" / CTR={fmt_pct(r.get('ctr'))} / CVR={fmt_pct(r.get('cvr'))}"
                f" / 応募CPA={fmt_num(r.get('obo_cpa')) if use_obo else 'N/A'}"
            )

        budget_progress = (
            f"{float(total.get('spend') or 0) / budget * 100:.1f}%" if budget and budget > 0 else 'N/A'
        )
        target_progress = (
            f"{float(total.get('cv') or 0) / target_cv * 100:.1f}%" if target_cv and target_cv > 0 else 'N/A'
        )
        line_cpa_total = fmt_num(total.get('cpa'))

        prompt = f"""
あなたはMeta広告運用の専門家です。以下のST（塾講師ステーション）KPIデータを分析し、4セクションのレポートを日本語で生成してください。

## 分析の前提・評価基準
- STは塾講師アルバイト・求人媒体サービス
- 最重要KPI: LINE登録CV → 応募CV（ナーチャリング経由。タイムラグ中央値40日）
- 直近40日以内の応募CVは過小評価の可能性あり（参考値として扱う）
- LINE登録CPA評価: ≤¥30,000=良好 / ≤¥50,000=要観察 / >¥50,000=要改善
- 応募CPA評価: ≤¥20,000=良好 / ≤¥30,000=要観察 / >¥30,000=要見直し
- 予算消化率: 85%未満=ペース遅れ / 85〜100%=適正 / 超過=要確認
- 広告名の命名規則: 先頭の番号＋アンダースコアが訴求軸（例: 01タイパ=タイパ訴求、02単願=単願訴求）
  CTA種別: LP=ペルソナLP / 診断=診断系フォーム / SNS=オーガニック組み合わせ

## 対象期間
{start_date} 〜 {end_date}（{week_label}）

## 全体KPI
- 広告費: {fmt_num(total.get('spend'))} / 月間予算: {fmt_num(budget)} / 予算進捗: {budget_progress}
- LINE登録CV: {total.get('cv')}件 / 月次目標: {target_cv}件 / 目標比: {target_progress}
- 全体LINE登録CPA: {line_cpa_total}
- 応募CV: {'N/A（BQ未分離）' if not use_obo else int(obo_cv_total)}件 / 全体応募CPA: {fmt_num(total.get('obo_cpa')) if use_obo else 'N/A'}
- CTR: {fmt_pct(total.get('ctr'))} / CVR: {fmt_pct(total.get('cvr'))}

## adset分類別KPI（当週）
{chr(10).join(group_lines) if group_lines else '※ ADSET_GROUPS未設定'}

## CTA別KPI（当週）
{chr(10).join(cta_lines)}

## クリエイティブ別KPI 上位15件（LINE登録CPA昇順）
{chr(10).join(top_ads_lines)}

---

## 出力指示

以下の4セクションを★見出し付きで記述すること。
仮説・推測には必ず証拠強度（★★★データで直接示せる事実 / ★★複数データが一致する間接推測 / ★論理的推定）を明記する。

★ 事象
- {week_label}の状況を具体的な数値（広告費・LINE_CV・CPA・CTR等）を3件以上引用して記述
- 「何が起きたか」を事実ベースで。評価や推測は含めない
- adset分類・CTA別・上位クリエイティブの特徴的な動きを必ず1つ以上言及

★ 要因仮説
- 「なぜその数値になったか」を証拠強度付きで3点
- 各点に必ずクリエイティブ名または訴求軸名（ad_nameや訴求の番号）と数値を引用
- 良好クリエイティブと不振クリエイティブの対比で説明すること

★ 示唆
▼WHO（このデータが示すターゲット層の状態・反応パターン。上位クリエイティブの共通点から読む）
▼WHAT（今週効いたメッセージ軸・訴求の共通要素。命名規則の訴求軸を使って説明）
▼HOW（次に打つべきクリエイティブ方向性・CTA選択・予算配分。具体的なクリエイティブ名・金額・割合で示す）

★ ネクスト
- 優先施策3点を証拠強度付きで
- 各施策は「誰が / 何を / いつまでに / 期待効果」の形式で記述
- 月間予算・目標達成の観点から優先順位を付けること

★ クリエイティブ要素
以下の評価軸で上位5件（CPA良好順）と下位2件（CPA不振）を分析すること。
動画を直接見ることはできないため、ad_name・scenario・CTR・CVRのデータから推定し、
各推定には証拠強度（★★★/★★/★）を必ず付けること。

評価軸:
1. フック（冒頭1〜3秒）: ターゲットが「自分ごと」と感じられるか
2. 字幕: テキスト量・視認性・キーワード配置の推定（ad_nameのコピー表現から判断）
3. BGM: ジャンル・テンポの推定（訴求トーンから推定。タイパ系=テンポ速め / 安心系=穏やか等）
4. 背景×内容の一致度: 訴求メッセージと想定される映像背景のマッチ度
5. CTAハードル: 「診断」<「LP遷移」<「直応募」の順にハードルが高い。CVRと照合して評価

出力形式（必ず表で）:
| クリエイティブ名(略) | フック | 字幕推定 | BGM推定 | 背景一致度 | CTAハードル | 評価コメント |
|---|---|---|---|---|---|---|

表の後に「要改善ポイント（下位2件）」を箇条書きで追記。
"""

        response = model.generate_content(prompt)
        raw_text = response.text

        def extract_section(text, header):
            pattern = rf'★\s*{re.escape(header)}\s*\n(.*?)(?=★\s|\Z)'
            m = re.search(pattern, text, re.DOTALL)
            return m.group(1).strip() if m else '[取得失敗]'

        gemini_texts['sesaku']   = extract_section(raw_text, '事象')
        gemini_texts['youin']    = extract_section(raw_text, '要因仮説')
        gemini_texts['shisa']    = extract_section(raw_text, '示唆')
        gemini_texts['next']     = extract_section(raw_text, 'ネクスト')
        gemini_texts['creative'] = extract_section(raw_text, 'クリエイティブ要素')
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
# STEP 6: コンソール出力
# ============================================================
period_str = f"{start_date} 〜 {end_date}"
days = (end_date - start_date).days + 1

def cpa_mark_emoji(mark):
    return {'OK': 'OK', 'CHECK': '△', 'NG': 'NG'}.get(mark, '-')

report = f"""
================================================================
  ST Meta広告 KPIレポート  {week_label}  {period_str}（{days}日間）
================================================================

【全体KPI】
広告費合計   : {fmt_num(total.get('spend'))}  / 予算: {fmt_num(budget)}  / 進捗: {f"{float(total.get('spend') or 0) / budget * 100:.1f}%" if budget else "N/A"}
LINE登録CV   : {int(total.get('cv') or 0)}件  / 目標: {target_cv}  / 目標比: {f"{float(total.get('cv') or 0) / target_cv * 100:.1f}%" if target_cv else "N/A"}
応募CV       : {'N/A（BQ未分離）' if not use_obo else int(obo_cv_total)}件
全体応募CPA  : {fmt_num(total.get('obo_cpa')) if use_obo else 'N/A'}
全体CTR      : {fmt_pct(total.get('ctr'))}  / CVR: {fmt_pct(total.get('cvr'))}

※ 直近40日以内の応募CVは過小評価の可能性あり（CTA→応募タイムラグ中央値40日）

---
【adset分類別KPI】（spend >= 1万円のみ / 応募CPA評価）

{'分類名':<20} {'spend':>12} {'LINE_CV':>8} {'応募CV':>8} {'応募CPA':>12} {'評価':>6} {'CTR':>8} {'CVR':>8}
{'-'*90}"""

for gname, g in group_totals.items():
    if gname == 'その他':
        continue
    report += (
        f"\n{gname:<20} {fmt_num(g['spend']):>12} {g['cv']:>8}"
        f" {str(int(g['obo_cv'])) if use_obo else 'N/A':>8}"
        f" {fmt_num(g['obo_cpa']):>12} {cpa_mark_emoji(g['cpa_mark']):>6}"
        f" {fmt_pct(g['ctr']):>8} {fmt_pct(g['cvr']):>8}"
    )

other = group_totals.get('その他', {})
if other:
    report += (
        f"\n{'その他':<20} {fmt_num(other.get('spend')):>12} {other.get('cv', 0):>8}"
        f" {'-':>8} {'-':>12} {'-':>6}"
        f" {fmt_pct(other.get('ctr')):>8} {fmt_pct(other.get('cvr')):>8}"
    )

report += f"""

評価凡例: OK=良好（応募CPA <= {CPA_THRESHOLDS['good']:,}円）/ △=要観察（<= {CPA_THRESHOLDS['ok']:,}円）/ NG=要見直し

---
【CTA別KPI（指定期間）】

{'CTA名':<20} {'spend':>12} {'LINE_CV':>8} {'応募CV':>8} {'応募CPA':>12}
{'-'*65}"""

for cta, t in cta_totals.items():
    if cta == 'その他':
        continue
    report += (
        f"\n{cta:<20} {fmt_num(t['spend']):>12} {t['cv']:>8}"
        f" {str(int(t['obo_cv'])) if use_obo else 'N/A':>8} {fmt_num(t['obo_cpa']):>12}"
    )

report += f"""

---
【上位クリエイティブ（LINE登録CPA順 / spend >= 1万円）】

{'広告名':<45} {'spend':>10} {'LINE_CV':>8} {'LINE_CPA':>12} {'CVR':>8}
{'-'*90}"""

for r in ad_rows[:15]:
    ad = str(r.get('ad_name') or '')[:43]
    report += (
        f"\n{ad:<45} {fmt_num(r.get('spend')):>10} {int(r.get('cv') or 0):>8}"
        f" {fmt_num(r.get('cpa')):>12} {fmt_pct(r.get('cvr')):>8}"
    )

report += f"""

---
★ 事象

{gemini_texts['sesaku']}

---
★ 要因仮説

{gemini_texts['youin']}

---
★ 示唆

{gemini_texts['shisa']}

---
★ ネクスト

{gemini_texts['next']}

---
★ クリエイティブ要素分析

{gemini_texts['creative']}

================================================================
"""

print(report)

# ============================================================
# JSON 保存
# ============================================================
output_file = os.path.join(_HERE, "kpi_report_st_data.json")
save_data = {
    'period_start': start_date.isoformat(),
    'period_end':   end_date.isoformat(),
    'week_label':   week_label,
    'total': {
        'spend':    float(total.get('spend') or 0),
        'cv':       int(total.get('cv') or 0),
        'obo_cv':   obo_cv_total if use_obo else None,
        'obo_cpa':  float(total.get('obo_cpa')) if use_obo and total.get('obo_cpa') else None,
        'ctr':      float(total.get('ctr')) if total.get('ctr') else None,
        'cvr':      float(total.get('cvr')) if total.get('cvr') else None,
        'budget':   budget,
        'target_cv': target_cv,
    },
    'group_totals': {
        gname: {
            'spend':   g['spend'],
            'cv':      g['cv'],
            'obo_cv':  g['obo_cv'] if use_obo else None,
            'obo_cpa': g['obo_cpa'],
            'cpa_mark': g['cpa_mark'],
        }
        for gname, g in group_totals.items()
    },
    'cta_totals': {
        cta: {'spend': t['spend'], 'cv': t['cv'], 'obo_cv': t['obo_cv'] if use_obo else None, 'obo_cpa': t['obo_cpa']}
        for cta, t in cta_totals.items()
    },
    'ad_rows': [
        {
            'ad_name':    str(r.get('ad_name') or ''),
            'adset_name': str(r.get('adset_name') or ''),
            'adset_group': classify_adset(r.get('adset_name')),
            'cta_group':  classify_cta(r.get('ad_name')),
            'spend':      float(r.get('spend') or 0),
            'cv':         int(r.get('cv') or 0),
            'obo_cv':     float(r.get('obo_cv') or 0) if use_obo else None,
            'cpa':        float(r.get('cpa')) if r.get('cpa') else None,
            'cvr':        float(r.get('cvr')) if r.get('cvr') else None,
            'scenario':   str(r.get('scenario') or '')[:100],
        }
        for r in ad_rows
    ],
    'gemini_texts': gemini_texts,
}

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(save_data, f, ensure_ascii=False, indent=2)
print(f"生データを {output_file} に保存しました。")

# ============================================================
# STEP 7: スプシ書き込み（--write フラグ時）
# ============================================================
if write_mode:
    print(f"\nKPI報告スプレッドシートに書き込みます。")
    from googleapiclient.discovery import build
    svc = build('sheets', 'v4', credentials=creds)

    # ---- ST_KPI報告シート: 当週列を特定 ----
    try:
        hdr = svc.spreadsheets().values().get(
            spreadsheetId=KPI_SHEET_ID,
            range=f"'{ST_KPI_SHEET}'!D10:R10",
            valueRenderOption='FORMATTED_VALUE'
        ).execute().get('values', [[]])[0]

        def col_letter(index):
            result = ''
            index += 1
            while index:
                index, remainder = divmod(index - 1, 26)
                result = chr(65 + remainder) + result
            return result

        week_col_idx  = hdr.index(week_label)  + 3 if week_label  in hdr else None
        cumul_col_idx = hdr.index(cumul_label) + 3 if cumul_label in hdr else None
        print(f"  週列: {col_letter(week_col_idx) if week_col_idx is not None else '未特定'} / 累積列: {col_letter(cumul_col_idx) if cumul_col_idx is not None else '未特定'}")
    except Exception as e:
        print(f"  ヘッダー特定スキップ: {e}")
        week_col_idx = cumul_col_idx = None

    batch_data = []

    if week_col_idx is not None:
        wc = col_letter(week_col_idx)
        batch_data += [
            {'range': f"'{ST_KPI_SHEET}'!{wc}15", 'values': [[int(total.get('cv') or 0)]]},
            {'range': f"'{ST_KPI_SHEET}'!{wc}27", 'values': [[float(total.get('spend') or 0)]]},
        ]
        if use_obo:
            obo_cpa_val = float(total.get('obo_cpa')) if total.get('obo_cpa') else None
            batch_data += [
                {'range': f"'{ST_KPI_SHEET}'!{wc}26", 'values': [[obo_cpa_val]]},
                {'range': f"'{ST_KPI_SHEET}'!{wc}35", 'values': [[int(obo_cv_total)]]},
            ]

    if cumul_col_idx is not None:
        cc = col_letter(cumul_col_idx)
        batch_data += [
            {'range': f"'{ST_KPI_SHEET}'!{cc}15", 'values': [[int(total.get('cv') or 0)]]},
            {'range': f"'{ST_KPI_SHEET}'!{cc}27", 'values': [[float(total.get('spend') or 0)]]},
        ]
        if use_obo:
            batch_data += [
                {'range': f"'{ST_KPI_SHEET}'!{cc}26", 'values': [[float(total.get('obo_cpa')) if total.get('obo_cpa') else None]]},
                {'range': f"'{ST_KPI_SHEET}'!{cc}35", 'values': [[int(obo_cv_total)]]},
            ]

    CTA_CV_ROWS = {'ペルソナLP': 45, '塾ブランド診断': 46, '気軽に診断': 47, '新1年生': 48, 'SNS ORG': 49}
    CTA_OBO_ROWS = {'ペルソナLP': 54, '塾ブランド診断': 55, '気軽に診断': 56, '新1年生': 57, 'SNS ORG': 58}

    if cumul_col_idx is not None:
        cc = col_letter(cumul_col_idx)
        for cta, row_num in CTA_CV_ROWS.items():
            val = cta_totals.get(cta, {}).get('cv')
            if val is not None:
                batch_data.append({'range': f"'{ST_KPI_SHEET}'!{cc}{row_num}", 'values': [[int(val)]]})
        if use_obo:
            for cta, row_num in CTA_OBO_ROWS.items():
                val = cta_totals.get(cta, {}).get('obo_cv')
                if val:
                    batch_data.append({'range': f"'{ST_KPI_SHEET}'!{cc}{row_num}", 'values': [[int(val)]]})

    if batch_data:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=KPI_SHEET_ID,
            body={'valueInputOption': 'USER_ENTERED', 'data': batch_data}
        ).execute()
        print(f"  ST_KPI報告 書き込み完了（{len(batch_data)}セル）")

    # ---- KPI報告 のコピーシート: 5セクションテキスト ----
    report_cells = [
        {'range': f"'{COPY_SHEET}'!P30",  'values': [[gemini_texts['sesaku']]]},
        {'range': f"'{COPY_SHEET}'!T30",  'values': [[gemini_texts['youin']]]},
        {'range': f"'{COPY_SHEET}'!X30",  'values': [[gemini_texts['shisa']]]},
        {'range': f"'{COPY_SHEET}'!AB30", 'values': [[gemini_texts['next']]]},
        # ラベル行
        {'range': f"'{COPY_SHEET}'!AF29", 'values': [['★クリエイティブ要素分析']]},
        # Gemini生成テキスト
        {'range': f"'{COPY_SHEET}'!AF30", 'values': [[gemini_texts['creative']]]},
    ]
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=KPI_SHEET_ID,
        body={'valueInputOption': 'RAW', 'data': report_cells}
    ).execute()
    print(f"  KPI報告 のコピー 書き込み完了（{len(report_cells)}セル）")
    print("\n完了。")

    save_data['report_texts'] = gemini_texts
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    # ============================================================
    # 月次データ更新: 'KPI報告 のコピー' AL2:AR10（チャート用）
    # create_monthly_charts.py で作成した8本のチャートの元データを更新する
    # チャート自体は固定参照のため、データ書き換えのみで自動反映される
    # ============================================================
    print("\n=== 月次データ更新（チャート用）===")
    try:
        monthly_query = f"""
WITH monthly AS (
  SELECT
    FORMAT_DATE('%m月', DATE_TRUNC(target_date, MONTH)) AS month_label,
    DATE_TRUNC(target_date, MONTH) AS month_date,
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS line_cv,
    COALESCE(SUM(custom_cv_2), 0) AS obo_cv,
    SUM(link_clicks)           AS link_clicks,
    SUM(impressions)           AS impressions
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 5 MONTH), MONTH)
  GROUP BY 1, 2
)
SELECT
  month_label,
  line_cv,
  obo_cv,
  SAFE_DIVIDE(spend, NULLIF(line_cv, 0))                 AS cpf,
  SAFE_DIVIDE(spend, NULLIF(obo_cv, 0))                  AS obo_cpa,
  spend,
  SAFE_DIVIDE(link_clicks, NULLIF(impressions, 0)) * 100 AS ctr,
  SAFE_DIVIDE(line_cv, NULLIF(link_clicks, 0))     * 100 AS cvr,
  SAFE_DIVIDE(spend, NULLIF(impressions, 0))       * 1000 AS cpm
FROM monthly
ORDER BY month_date
"""
        m_rows = list(client.query(monthly_query).result())
        m_data = []
        for r in m_rows:
            obo_v  = float(r['obo_cv'] or 0)
            line_v = float(r['line_cv'] or 0)
            # custom_cv_2 が 0 または LINE登録CVと同値の月は応募CV無効とする
            obo_valid = obo_v > 0 and obo_v != line_v
            m_data.append({
                'month_label': r['month_label'],
                'line_cv':     int(line_v),
                'obo_cv':      int(obo_v)                          if obo_valid else '',
                'obo_cpa':     round(float(r['obo_cpa']), 0)       if (obo_valid and r['obo_cpa']) else '',
                'cpf':         round(float(r['cpf']), 0)           if r['cpf'] else '',
                'spend':       round(float(r['spend'] or 0), 0),
                'ctr':         round(float(r['ctr']), 2)           if r['ctr'] else '',
                'cvr':         round(float(r['cvr']), 2)           if r['cvr'] else '',
                'cpm':         round(float(r['cpm']), 0)           if r['cpm'] else '',
            })
        months   = [d['month_label'] for d in m_data]
        num_cols = len(m_data)  # 実際の月数（通常6）

        def monthly_col_letter(idx):
            result = ''
            idx += 1
            while idx:
                idx, r = divmod(idx - 1, 26)
                result = chr(65 + r) + result
            return result

        label_col = monthly_col_letter(37)  # AL
        end_col   = monthly_col_letter(38 + num_cols - 1)  # AM + (num_cols-1)

        m_sheet_data = [
            ['月']         + months,
            ['LINE登録CV'] + [d['line_cv']  for d in m_data],
            ['応募CV']     + [d['obo_cv']   for d in m_data],  # obo_valid=Falseの月は空文字
            ['応募CPA']    + [d['obo_cpa']  for d in m_data],  # 同上
            ['COST']       + [d['spend']    for d in m_data],
            ['CPF']        + [d['cpf']      for d in m_data],
            ['CTR(%)']     + [d['ctr']      for d in m_data],
            ['CVR(%)']     + [d['cvr']      for d in m_data],
            ['CPM']        + [d['cpm']      for d in m_data],
        ]
        # 書き込み前に全範囲クリア（前回より月数が少ない場合に古いデータが残るのを防ぐ）
        svc.spreadsheets().values().clear(
            spreadsheetId=KPI_SHEET_ID,
            range=f"'{COPY_SHEET}'!AL2:AR10"
        ).execute()
        svc.spreadsheets().values().update(
            spreadsheetId=KPI_SHEET_ID,
            range=f"'{COPY_SHEET}'!{label_col}2:{end_col}10",
            valueInputOption='USER_ENTERED',
            body={'values': m_sheet_data}
        ).execute()
        print(f"  月次データ更新完了: {label_col}2:{end_col}10 ({num_cols}ヶ月: {', '.join(months)})")
    except Exception as e:
        print(f"  [月次データ更新エラー] {e}")

    # ============================================================
    # STEP 7b: v2 タブへの書き込み（--v2 フラグ時）
    # 集計さん構造: 行4-19（週次KPI）+ 行33-49（CTA別）+ 右側ダッシュボード
    # ============================================================
    if v2_mode:
        print(f"\n=== STEP 7b: ST_KPI報告_v2 タブへの書き込み ===")
        from calendar import monthrange

        # 月初・月末・消化率の計算
        month_start   = start_date.replace(day=1)
        days_in_month = monthrange(start_date.year, start_date.month)[1]
        elapsed_days  = (end_date - month_start).days + 1
        progress_rate = elapsed_days / days_in_month

        # 着地見込み・ビハインド計算
        actual_spend   = float(total.get('spend') or 0)
        actual_line_cv = int(total.get('cv') or 0)
        actual_obo_cv  = obo_cv_total if use_obo else None

        projected_cost    = actual_spend / progress_rate
        projected_line_cv = actual_line_cv / progress_rate
        projected_obo_cv  = actual_obo_cv / progress_rate if actual_obo_cv is not None else None

        cost_over   = projected_cost - budget if budget else None
        behind_line = projected_line_cv - target_cv if target_cv else None
        behind_obo  = projected_obo_cv - target_cv if (projected_obo_cv is not None and target_cv) else None

        total_cpf     = float(total.get('cpa') or 0) or None    # LINE登録CPA = spend/LINE_CV
        total_cvr     = float(total.get('cvr') or 0) or None
        total_ctr     = float(total.get('ctr') or 0) or None
        total_cpm     = float(total.get('cpm') or 0) or None
        total_imp     = int(total.get('impressions') or 0)
        total_obo_cpa = float(total.get('obo_cpa')) if use_obo and total.get('obo_cpa') else None
        total_conv    = actual_obo_cv / actual_line_cv * 100 if (
            use_obo and actual_line_cv > 0 and actual_obo_cv
        ) else None

        print(f"  消化率: {progress_rate:.1%}  着地見込みCOST: {fmt_num(projected_cost)}")
        print(f"  着地見込みLINE_CV: {projected_line_cv:.0f}  ビハインド: {f'{behind_line:+.0f}' if behind_line is not None else 'N/A'}")

        try:
            # 週ヘッダー行（行2, B-P）を読んで列インデックス確定
            hdr_v2 = svc.spreadsheets().values().get(
                spreadsheetId=KPI_SHEET_ID,
                range=f"'{ST_KPI_SHEET_V2}'!B2:P2",
                valueRenderOption='FORMATTED_VALUE',
            ).execute().get('values', [[]])[0]

            wc_idx  = hdr_v2.index(week_label)  + 1 if week_label  in hdr_v2 else None
            cc_idx  = hdr_v2.index(cumul_label) + 1 if cumul_label in hdr_v2 else None
            print(f"  週列: {col_letter(wc_idx) if wc_idx else '未特定'} / 累積列: {col_letter(cc_idx) if cc_idx else '未特定'}")

            v2_data = []

            # ----- 週次・累積 KPI 書き込み -----
            # v2 行番号: LINE登録CV=4 / CPF=7 / COST=8 / IMP=9 / CTR=10 / CVR=11 / CPM=12
            #           応募CV=15 / 応募CPA=18 / 転換率=19
            WEEKLY_KPI = [
                (4,  actual_line_cv),
                (7,  total_cpf),
                (8,  actual_spend),
                (9,  total_imp if total_imp else None),
                (10, total_ctr),
                (11, total_cvr),
                (12, total_cpm),
                (15, actual_obo_cv),
                (18, total_obo_cpa),
                (19, total_conv),
            ]
            for col_idx in [wc_idx, cc_idx]:
                if col_idx is None:
                    continue
                cl = col_letter(col_idx)
                for row_num, val in WEEKLY_KPI:
                    if val is not None:
                        v2_data.append({
                            'range': f"'{ST_KPI_SHEET_V2}'!{cl}{row_num}",
                            'values': [[round(val, 2) if isinstance(val, float) else val]],
                        })

            # ----- CTA別テーブル（行35-40）友達獲得 -----
            # 列: B=LINE登録CV / C=COST / D=CPF / E=応募CV / F=転換率 / G=応募CPA
            CTA_LINE_ROW = {
                'ペルソナLP':    35,
                '塾ブランド診断': 36,
                '気軽に診断':    37,
                '新1年生':       38,
                'SNS ORG':       39,
                '合計':          40,
            }
            # 合計行用の集計
            total_cta = {
                'cv':      actual_line_cv,
                'spend':   actual_spend,
                'cpf':     total_cpf,
                'obo_cv':  actual_obo_cv,
                'conv_rate': total_conv,
                'obo_cpa': total_obo_cpa,
            }
            for cta, row_num in CTA_LINE_ROW.items():
                t = total_cta if cta == '合計' else cta_totals.get(cta, {})
                for col_letter_v, field in [
                    ('B', 'cv'), ('C', 'spend'), ('D', 'cpf'),
                    ('E', 'obo_cv'), ('F', 'conv_rate'), ('G', 'obo_cpa'),
                ]:
                    val = t.get(field)
                    if val is not None:
                        v2_data.append({
                            'range': f"'{ST_KPI_SHEET_V2}'!{col_letter_v}{row_num}",
                            'values': [[round(val, 2) if isinstance(val, float) else val]],
                        })

            # ----- CTA別テーブル（行44-49）LINE応募 -----
            # 列: B=応募CV / C=応募CPA / D=転換率
            CTA_OBO_ROW = {
                'ペルソナLP':    44,
                '塾ブランド診断': 45,
                '気軽に診断':    46,
                '新1年生':       47,
                'SNS ORG':       48,
                '合計':          49,
            }
            for cta, row_num in CTA_OBO_ROW.items():
                t = total_cta if cta == '合計' else cta_totals.get(cta, {})
                for col_letter_v, field in [
                    ('B', 'obo_cv'), ('C', 'obo_cpa'), ('D', 'conv_rate'),
                ]:
                    val = t.get(field)
                    if val is not None:
                        v2_data.append({
                            'range': f"'{ST_KPI_SHEET_V2}'!{col_letter_v}{row_num}",
                            'values': [[round(val, 2) if isinstance(val, float) else val]],
                        })

            # ----- 右側ダッシュボード（列S-V, 行5-9）-----
            # S=実績 / T=目標/予算（入力タブから、T列は手動入力なのでここでは書かない）
            # U=着地見込み / V=ビハインド/超過
            DASH_ROWS = [
                # (row, actual, projected, behind_or_over)
                (5, actual_spend,    projected_cost,    cost_over),
                (6, actual_line_cv,  projected_line_cv, behind_line),
                (7, actual_obo_cv,   projected_obo_cv,  behind_obo),
                (8, total_obo_cpa,   None,              None),
                (9, total_cpf,       None,              None),
            ]
            for row_num, actual, projected, deviation in DASH_ROWS:
                if actual is not None:
                    v2_data.append({
                        'range': f"'{ST_KPI_SHEET_V2}'!S{row_num}",
                        'values': [[round(actual, 0) if isinstance(actual, float) else actual]],
                    })
                if projected is not None:
                    v2_data.append({
                        'range': f"'{ST_KPI_SHEET_V2}'!U{row_num}",
                        'values': [[round(projected, 0)]],
                    })
                if deviation is not None:
                    v2_data.append({
                        'range': f"'{ST_KPI_SHEET_V2}'!V{row_num}",
                        'values': [[round(deviation, 0)]],
                    })
            # 予算・目標も T 列に書き込む（入力タブ参照値）
            if budget:
                v2_data.append({'range': f"'{ST_KPI_SHEET_V2}'!T5", 'values': [[budget]]})
            if target_cv:
                v2_data.append({'range': f"'{ST_KPI_SHEET_V2}'!T6", 'values': [[target_cv]]})

            if v2_data:
                svc.spreadsheets().values().batchUpdate(
                    spreadsheetId=KPI_SHEET_ID,
                    body={'valueInputOption': 'USER_ENTERED', 'data': v2_data},
                ).execute()
                print(f"  v2 書き込み完了（{len(v2_data)} セル）")
            else:
                print("  v2: 書き込みデータなし（週ヘッダーが見つからない可能性あり）")

        except Exception as e:
            print(f"  [v2 書き込みエラー] {e}")

    # ============================================================
    # STEP 7c: 新独立KPIシート（BQ版）への書き込み（--new-sheet フラグ時）
    # 集計さんKPI報告タブと同一の行構造（create_kpi_report_standalone.py で作成済み）
    # ============================================================
    if new_sheet_mode:
        print(f"\n=== STEP 7c: 新KPIシート（BQ版）への書き込み ===")
        try:
            # 行10のラベルを読んで週列を特定
            hdr_new = svc.spreadsheets().values().get(
                spreadsheetId=NEW_KPI_SHEET_ID,
                range=f"'{NEW_KPI_TAB}'!D10:M10",
                valueRenderOption='FORMATTED_VALUE'
            ).execute().get('values', [[]])[0]

            wc_new = None
            if week_label in hdr_new:
                wc_new = col_letter(hdr_new.index(week_label) + 3)
                print(f"  週列: {wc_new}（{week_label}）")
            else:
                print(f"  [警告] 週ラベル '{week_label}' が行10に見つかりません。日付ヘッダーが自動生成されているか確認してください。")

            if wc_new:
                ns = NEW_KPI_TAB
                nd = []

                # 全体KPI
                line_cv_val  = int(total.get('cv') or 0)
                spend_val    = float(total.get('spend') or 0)
                clicks_val   = int(total.get('link_clicks') or 0)
                imp_val      = int(total.get('impressions') or 0)
                line_cpa_val = round(spend_val / line_cv_val, 0) if line_cv_val > 0 else None

                nd += [
                    {'range': f"'{ns}'!{wc_new}15", 'values': [[line_cv_val]]},       # LINE_CV
                    {'range': f"'{ns}'!{wc_new}17", 'values': [[clicks_val]]},         # CT（link_clicks）
                    {'range': f"'{ns}'!{wc_new}19", 'values': [[imp_val]]},             # IMP
                    {'range': f"'{ns}'!{wc_new}25", 'values': [[line_cpa_val]]},        # LINE登録CPA
                    {'range': f"'{ns}'!{wc_new}27", 'values': [[spend_val]]},           # COST
                ]

                if use_obo and obo_cv_total:
                    obo_cpa_val = round(spend_val / obo_cv_total, 0) if obo_cv_total > 0 else None
                    nd += [
                        {'range': f"'{ns}'!{wc_new}11", 'values': [[int(obo_cv_total)]]},  # 応募CV
                        {'range': f"'{ns}'!{wc_new}13", 'values': [[clicks_val]]},          # CT（再掲）
                        {'range': f"'{ns}'!{wc_new}14", 'values': [[obo_cpa_val]]},         # 応募CPA
                        {'range': f"'{ns}'!{wc_new}26", 'values': [[obo_cpa_val]]},         # 応募CPA（再掲）
                    ]

                # CTA別 LINE登録CV（行45-49）
                CTA_CV_ROWS_NEW  = {'ペルソナLP': 45, '塾ブランド診断': 46, '気軽に診断': 47, '新1年生': 48, 'SNS ORG': 49}
                # CTA別 COST（行50-53 ※ORGなし）
                CTA_COST_ROWS_NEW = {'ペルソナLP': 50, '塾ブランド診断': 51, '気軽に診断': 52, '新1年生': 53}
                # CTA別 応募CV（行54-58）
                CTA_OBO_ROWS_NEW = {'ペルソナLP': 54, '塾ブランド診断': 55, '気軽に診断': 56, '新1年生': 57, 'SNS ORG': 58}

                for cta, row_num in CTA_CV_ROWS_NEW.items():
                    val = cta_totals.get(cta, {}).get('cv')
                    if val is not None:
                        nd.append({'range': f"'{ns}'!{wc_new}{row_num}", 'values': [[int(val)]]})

                for cta, row_num in CTA_COST_ROWS_NEW.items():
                    val = cta_totals.get(cta, {}).get('spend')
                    if val is not None:
                        nd.append({'range': f"'{ns}'!{wc_new}{row_num}", 'values': [[round(float(val), 0)]]})

                if use_obo:
                    for cta, row_num in CTA_OBO_ROWS_NEW.items():
                        val = cta_totals.get(cta, {}).get('obo_cv')
                        if val:
                            nd.append({'range': f"'{ns}'!{wc_new}{row_num}", 'values': [[int(val)]]})

                if nd:
                    svc.spreadsheets().values().batchUpdate(
                        spreadsheetId=NEW_KPI_SHEET_ID,
                        body={'valueInputOption': 'USER_ENTERED', 'data': nd}
                    ).execute()
                    print(f"  新KPIシート 書き込み完了（{len(nd)}セル）")

        except Exception as e:
            print(f"  [新KPIシート書き込みエラー] {e}")

else:
    print(f"\nスプシ書き込みを実行するには: python3 scripts/kpi_report_st.py {date_arg} --write")
