"""
ST Meta広告 深掘り分析レポート（直近90日）
- 訴求軸別 CPA/CVR Bootstrap 95%CI
- 季節変数フィット検証（9月）
- 週次トレンド線形回帰
- クリエイティブライフサイクル分析
- Google Doc出力

必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth google-api-python-client
"""
import sys, io, time, random, math, re
from datetime import datetime, timedelta
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
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

bq_client = bigquery.Client(project="bigquery-jukust", credentials=creds)
docs_svc  = build("docs", "v1", credentials=creds, cache_discovery=False)

BQ_VIEW = "bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report"

# ── BigQueryクエリ ──────────────────────────────────────────────────

# 広告別90日集計（訴求軸分析用）
Q_AD = f"""
WITH base AS (
  SELECT
    target_date,
    ad_name,
    campaign_name,
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
    ad_name,
    campaign_name,
    SUM(spend)       AS spend,
    SUM(link_clicks) AS clicks,
    SUM(line_cv)     AS line_cv,
    SUM(impressions) AS impressions,
    MIN(target_date) AS date_from,
    MAX(target_date) AS date_to
  FROM base
  GROUP BY ad_name, campaign_name
)
SELECT
  ad_name,
  campaign_name,
  spend,
  clicks,
  line_cv,
  impressions,
  date_from,
  date_to,
  SAFE_DIVIDE(spend, line_cv)           AS cpa,
  SAFE_DIVIDE(line_cv, clicks)          AS cvr,
  SAFE_DIVIDE(clicks, impressions)      AS ctr,
  DATE_DIFF(date_to, date_from, DAY)    AS age_days
FROM agg
WHERE spend >= 10000
ORDER BY spend DESC
"""

# 週次トレンド（全体）
Q_WEEKLY = f"""
WITH base AS (
  SELECT
    target_date,
    spend,
    link_clicks,
    complete_registration AS line_cv,
    impressions
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    AND target_date < CURRENT_DATE()
)
SELECT
  DATE_TRUNC(target_date, WEEK(MONDAY)) AS week_start,
  SUM(spend)       AS spend,
  SUM(link_clicks) AS clicks,
  SUM(line_cv)     AS line_cv,
  SUM(impressions) AS impressions,
  SAFE_DIVIDE(SUM(spend), SUM(line_cv))           AS cpa,
  SAFE_DIVIDE(SUM(line_cv), SUM(link_clicks))     AS cvr,
  SAFE_DIVIDE(SUM(link_clicks), SUM(impressions)) AS ctr
FROM base
GROUP BY week_start
ORDER BY week_start
"""

print("BigQueryからデータ取得中（直近90日）...")
ad_rows   = list(bq_client.query(Q_AD).result())
week_rows = list(bq_client.query(Q_WEEKLY).result())
print(f"  広告別: {len(ad_rows)}件（spend >= 1万円）")
print(f"  週次集計: {len(week_rows)}週")

# ── 分類関数 ────────────────────────────────────────────────────────

def classify_axis(ad_name: str) -> str:
    """旧命名: 01タイパ_, 02単願_, 03併願_ / 新命名: 軸コードA-I"""
    n = ad_name or ''
    if re.search(r'01タイパ', n):   return 'タイパ'
    if re.search(r'02単願',  n):   return '単願'
    if re.search(r'03併願',  n):   return '併願'
    if re.search(r'App_',    n, re.I): return 'App(LP)'
    if re.search(r'タイパ|タイムパ', n): return 'タイパ'
    if re.search(r'単願',    n):   return '単願'
    if re.search(r'併願',    n):   return '併願'
    return 'その他'

def classify_media(ad_name: str) -> str:
    n = ad_name or ''
    if re.search(r'NP_|EP_|静止画|画像', n, re.I): return '静止画'
    if re.search(r'NV_|EV_|動画',        n, re.I): return '動画'
    if re.search(r'App_',               n, re.I): return 'App'
    return '動画'  # default

def classify_cta(ad_name: str, campaign_name: str) -> str:
    n  = (ad_name or '').lower()
    cn = (campaign_name or '').lower()
    if 'brandtest' in n or 'ブランド診断' in n: return 'ブランド診断'
    if '気軽' in n or '診断' in n:             return '気軽に診断'
    if 'sns_org' in n or 'app_' in n.lower():  return 'App(SNS_ORG)'
    if 'app' in cn:                            return 'App(LP)'
    return 'ペルソナLP'

# 各行に属性付与
rows = []
for r in ad_rows:
    axis  = classify_axis(r['ad_name'])
    media = classify_media(r['ad_name'])
    cta   = classify_cta(r['ad_name'], r['campaign_name'])
    rows.append({
        'ad_name':   r['ad_name'],
        'campaign':  r['campaign_name'],
        'spend':     float(r['spend']   or 0),
        'clicks':    float(r['clicks']  or 0),
        'cv':        float(r['line_cv'] or 0),
        'imps':      float(r['impressions'] or 0),
        'cpa':       float(r['cpa']     or 0) if r['cpa'] else None,
        'cvr':       float(r['cvr']     or 0) if r['cvr'] else None,
        'ctr':       float(r['ctr']     or 0) if r['ctr'] else None,
        'age_days':  int(r['age_days']  or 0),
        'date_from': str(r['date_from']),
        'date_to':   str(r['date_to']),
        'axis':      axis,
        'media':     media,
        'cta':       cta,
    })

# ── 統計関数（純粋Python・ライブラリ不要） ─────────────────────────

def weighted_cpa(group_rows: list) -> float:
    """spend加重CPA"""
    ts = sum(r['spend'] for r in group_rows)
    tv = sum(r['cv']    for r in group_rows)
    return ts / tv if tv > 0 else float('inf')

def bootstrap_cpa(group_rows: list, n_boot: int = 2000, seed: int = 42) -> dict:
    """Bootstrap 95%CI for spend-weighted CPA"""
    rng = random.Random(seed)
    if not group_rows:
        return {'cpa': None, 'lo95': None, 'hi95': None, 'n': 0}
    n   = len(group_rows)
    obs = weighted_cpa(group_rows)
    boot_cpas = []
    for _ in range(n_boot):
        sample = rng.choices(group_rows, k=n)
        c = weighted_cpa(sample)
        if c != float('inf'):
            boot_cpas.append(c)
    if not boot_cpas:
        return {'cpa': obs, 'lo95': None, 'hi95': None, 'n': n}
    boot_cpas.sort()
    lo = boot_cpas[int(0.025 * len(boot_cpas))]
    hi = boot_cpas[int(0.975 * len(boot_cpas))]
    return {'cpa': obs, 'lo95': lo, 'hi95': hi, 'n': n}

def permutation_test(a_rows: list, b_rows: list, n_perm: int = 2000, seed: int = 42) -> dict:
    """CPA差の置換検定（双側）"""
    rng = random.Random(seed)
    all_rows = a_rows + b_rows
    na, nb   = len(a_rows), len(b_rows)
    obs_a    = weighted_cpa(a_rows)
    obs_b    = weighted_cpa(b_rows)
    obs_diff = obs_b - obs_a  # B - A
    count    = 0
    for _ in range(n_perm):
        rng.shuffle(all_rows)
        perm_a = all_rows[:na]
        perm_b = all_rows[na:]
        d = weighted_cpa(perm_b) - weighted_cpa(perm_a)
        if abs(d) >= abs(obs_diff):
            count += 1
    p_val = count / n_perm
    return {
        'cpa_a': obs_a, 'cpa_b': obs_b,
        'diff': obs_diff,
        'p_value': p_val,
        'significant': p_val < 0.05
    }

def linear_regression(xs: list, ys: list) -> dict:
    """OLS単回帰 slope / intercept / R²"""
    n = len(xs)
    if n < 2:
        return {'slope': None, 'intercept': None, 'r2': None}
    mx = sum(xs) / n
    my = sum(ys) / n
    ss_xy = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
    ss_xx = sum((xs[i]-mx)**2         for i in range(n))
    if ss_xx == 0:
        return {'slope': 0, 'intercept': my, 'r2': None}
    slope = ss_xy / ss_xx
    intercept = my - slope * mx
    y_hat = [slope*xs[i] + intercept for i in range(n)]
    ss_res = sum((ys[i]-y_hat[i])**2 for i in range(n))
    ss_tot = sum((ys[i]-my)**2        for i in range(n))
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
    return {'slope': slope, 'intercept': intercept, 'r2': r2}

# ── 分析実施 ─────────────────────────────────────────────────────────

print("\n訴求軸別 Bootstrap CPA分析中...")
axes = ['タイパ', '単願', '併願', 'App(LP)', 'その他']
axis_stats = {}
for ax in axes:
    grp = [r for r in rows if r['axis'] == ax and r['cv'] > 0]
    all_grp = [r for r in rows if r['axis'] == ax]
    bs = bootstrap_cpa(grp)
    axis_stats[ax] = {
        **bs,
        'n_ads':    len(all_grp),
        'n_cv_ads': len(grp),
        'spend':    sum(r['spend'] for r in all_grp),
        'cv':       sum(r['cv']   for r in all_grp),
        'cvr':      sum(r['cv'] for r in all_grp) / sum(r['clicks'] for r in all_grp) if sum(r['clicks'] for r in all_grp) > 0 else None,
        'ctr':      sum(r['clicks'] for r in all_grp) / sum(r['imps'] for r in all_grp) if sum(r['imps'] for r in all_grp) > 0 else None,
    }
    cpa_str = f"¥{bs['cpa']:,.0f}" if bs['cpa'] else '—'
    lo_str  = f"¥{bs['lo95']:,.0f}" if bs['lo95'] else '?'
    hi_str  = f"¥{bs['hi95']:,.0f}" if bs['hi95'] else '?'
    print(f"  {ax}: CPA={cpa_str} [{lo_str} - {hi_str}] n={bs['n']}")

print("\nタイパ vs 単願 置換検定中（2000回）...")
taipa_rows = [r for r in rows if r['axis'] == 'タイパ' and r['cv'] > 0]
tanwan_rows = [r for r in rows if r['axis'] == '単願' and r['cv'] > 0]
perm_result = permutation_test(taipa_rows, tanwan_rows)
print(f"  タイパCPA={perm_result['cpa_a']:,.0f} vs 単願CPA={perm_result['cpa_b']:,.0f}  p={perm_result['p_value']:.3f}")

print("\nCTA別 Bootstrap CPA分析中...")
cta_types = list(set(r['cta'] for r in rows))
cta_stats = {}
for ct in cta_types:
    grp = [r for r in rows if r['cta'] == ct and r['cv'] > 0]
    all_grp = [r for r in rows if r['cta'] == ct]
    bs = bootstrap_cpa(grp)
    cta_stats[ct] = {
        **bs,
        'n_ads': len(all_grp),
        'spend': sum(r['spend'] for r in all_grp),
        'cv':    sum(r['cv']   for r in all_grp),
    }

print("\nメディア別分析中...")
media_types = ['動画', '静止画', 'App']
media_stats = {}
for mt in media_types:
    grp = [r for r in rows if r['media'] == mt and r['cv'] > 0]
    all_grp = [r for r in rows if r['media'] == mt]
    bs = bootstrap_cpa(grp)
    media_stats[mt] = {
        **bs,
        'n_ads': len(all_grp),
        'spend': sum(r['spend'] for r in all_grp),
        'cv':    sum(r['cv']   for r in all_grp),
    }

print("\n週次トレンド回帰分析中...")
w_rows = [r for r in week_rows if r['cpa'] and r['cvr'] and r['ctr']]
w_xs   = list(range(len(w_rows)))
w_cpas = [float(r['cpa']) for r in w_rows]
w_cvrs = [float(r['cvr']) for r in w_rows]
w_ctrs = [float(r['ctr']) for r in w_rows]
reg_cpa = linear_regression(w_xs, w_cpas)
reg_cvr = linear_regression(w_xs, w_cvrs)
reg_ctr = linear_regression(w_xs, w_ctrs)
print(f"  CPA slope={reg_cpa['slope']:+.0f}/週  R²={reg_cpa['r2']:.3f}")
print(f"  CVR slope={reg_cvr['slope']:+.4f}/週  R²={reg_cvr['r2']:.3f}")

print("\nクリエイティブライフサイクル分析中...")
lifecycle = {'新鮮(≤30日)': [], '中堅(31-60日)': [], '熟成(>60日)': []}
for r in rows:
    if r['cv'] > 0:
        if r['age_days'] <= 30:  lifecycle['新鮮(≤30日)'].append(r)
        elif r['age_days'] <= 60: lifecycle['中堅(31-60日)'].append(r)
        else:                     lifecycle['熟成(>60日)'].append(r)
life_stats = {}
for k, grp in lifecycle.items():
    bs = bootstrap_cpa(grp)
    life_stats[k] = {**bs, 'n': len(grp), 'spend': sum(r['spend'] for r in grp), 'cv': sum(r['cv'] for r in grp)}

# ライフサイクル vs CPA 回帰
age_xs  = [r['age_days'] for r in rows if r['cpa'] and r['cv'] > 0]
age_cpa = [r['cpa']      for r in rows if r['cpa'] and r['cv'] > 0]
reg_age = linear_regression(age_xs, age_cpa)

print("\n季節変数フィット検証（9月）...")
# 9月推奨: タイパ35% / 単願40% / 併願25%
SEASONAL_RECOMMENDED = {'タイパ': 0.35, '単願': 0.40, '併願': 0.25}
total_spend = sum(r['spend'] for r in rows if r['axis'] in SEASONAL_RECOMMENDED)
actual_dist  = {}
for ax in SEASONAL_RECOMMENDED:
    ax_spend = sum(r['spend'] for r in rows if r['axis'] == ax)
    actual_dist[ax] = ax_spend / total_spend if total_spend > 0 else 0
    print(f"  {ax}: 実績={actual_dist[ax]*100:.1f}%  推奨={SEASONAL_RECOMMENDED[ax]*100:.0f}%  差={actual_dist[ax]-SEASONAL_RECOMMENDED[ax]:+.1%}")

# ── 出力用フォーマット ───────────────────────────────────────────────

def fy(v, d=0):
    """yen format"""
    if v is None or v == float('inf'): return '—'
    return f"¥{v:,.{d}f}"

def fp(v, d=2):
    """percent format"""
    if v is None: return '—'
    return f"{v*100:.{d}f}%"

def fb(stat):
    """Bootstrap CI string"""
    if stat['cpa'] is None: return '—'
    if stat['lo95'] is None: return f"{fy(stat['cpa'])} (CI算出不可)"
    return f"{fy(stat['cpa'])} [{fy(stat['lo95'])} - {fy(stat['hi95'])}]"

# ── Google Doc本文構築 ──────────────────────────────────────────────

today = datetime.now().strftime('%Y-%m-%d')
lines = []

lines.append(f"ST Meta広告 深掘り分析レポート（直近90日）\n")
lines.append(f"作成: {today}  |  対象: 直近90日 spend≥1万円の広告 {len(rows)}件\n")
lines.append("※ CV値はBigQuery集計値。管理画面との照合が必要（ビュースルーCV含む可能性あり）。\n")
lines.append("※ 統計手法: Bootstrap 95%CI（n=2000）、置換検定（n=2000）、OLS線形回帰\n")
lines.append("\n")

# ── セクション0: エグゼクティブサマリー ──
lines.append("【0. エグゼクティブサマリー】\n")
total_cv   = sum(r['cv']    for r in rows)
total_sp   = sum(r['spend'] for r in rows)
best_ax    = min([(ax, axis_stats[ax]) for ax in ['タイパ','単願','併願'] if axis_stats[ax]['cpa']], key=lambda x: x[1]['cpa'], default=('—', {}))
worst_zero = [r for r in rows if r['cv'] == 0]

lines.append(f"■ 全体概要\n")
lines.append(f"  消化合計: {fy(total_sp)}  |  LINE_CV合計: {total_cv:.0f}件  |  全体CPA: {fy(total_sp/total_cv if total_cv else None)}\n")
lines.append(f"  対象広告数: {len(rows)}件（CV>0: {sum(1 for r in rows if r['cv']>0)}件 / CV=0: {len(worst_zero)}件）\n")
lines.append("\n")
lines.append(f"■ 主要インサイト（3点）\n")
lines.append(f"  ① 最良訴求軸: {best_ax[0]}（CPA {fy(best_ax[1].get('cpa'))} / 95%CI {fb(best_ax[1])}）\n")
sig_text = "有意差あり(p<0.05)" if perm_result['significant'] else f"有意差なし(p={perm_result['p_value']:.3f})"
lines.append(f"  ② タイパ vs 単願 CPA差: {sig_text}\n")
cpa_trend = "上昇傾向" if (reg_cpa['slope'] or 0) > 0 else "下降傾向（改善）"
r2_txt = f"R²={reg_cpa['r2']:.3f}" if reg_cpa['r2'] is not None else ''
lines.append(f"  ③ 週次CPA: {cpa_trend}（slope={reg_cpa['slope']:+.0f}円/週 {r2_txt}）\n")
lines.append("\n")

# ── セクション1: 訴求軸別分析 ──
lines.append("【1. 訴求軸別 CPA / CVR 分析（Bootstrap 95%CI）】\n")
lines.append("訴求軸          広告数  CV  消化            CPA（95%CI）                      CVR\n")
lines.append("─" * 110 + "\n")
for ax in axes:
    st = axis_stats.get(ax)
    if not st: continue
    ci_str = fb(st)
    lines.append(
        f"{ax:<14}  {st['n_ads']:>4}件  {st['cv']:>4.0f}  {fy(st['spend']):>12}  "
        f"{ci_str:<38}  {fp(st['cvr'])}\n"
    )
lines.append("\n")
lines.append("■ 解釈（証拠強度）\n")
lines.append(f"  ・{best_ax[0]}訴求が最良CPA（★★★: BQデータ90日実績）\n")
lines.append(f"  ・タイパ vs 単願: {sig_text}（★★★: 置換検定 n=2000）\n")
if perm_result['significant']:
    winner = 'タイパ' if perm_result['cpa_a'] < perm_result['cpa_b'] else '単願'
    lines.append(f"  ・{winner}の優位が統計的に確認されており、予算配分の最適化を推奨\n")
else:
    lines.append("  ・現時点でどちらが優位か断言できない。データ蓄積後に再検定が必要\n")
lines.append("\n")

# タイパ vs 単願 置換検定詳細
lines.append("■ タイパ vs 単願 置換検定詳細\n")
lines.append(f"  タイパCPA: {fy(perm_result['cpa_a'])}  (n={len(taipa_rows)}件の広告)\n")
lines.append(f"  単願  CPA: {fy(perm_result['cpa_b'])}  (n={len(tanwan_rows)}件の広告)\n")
lines.append(f"  差分(単願-タイパ): {fy(abs(perm_result['diff']))}\n")
lines.append(f"  p値: {perm_result['p_value']:.3f}  →  {'有意(p<0.05)' if perm_result['significant'] else '非有意(p≥0.05)'}\n")
lines.append("\n")

# ── セクション2: CTA別分析 ──
lines.append("【2. CTA別 CPA 分析（Bootstrap 95%CI）】\n")
lines.append("CTA種別          広告数  CV    消化            CPA（95%CI）\n")
lines.append("─" * 100 + "\n")
for ct, st in sorted(cta_stats.items(), key=lambda x: (x[1]['cpa'] or float('inf'))):
    if st['n_ads'] == 0: continue
    lines.append(
        f"{ct:<16}  {st['n_ads']:>4}件  {st['cv']:>4.0f}  {fy(st['spend']):>12}  {fb(st)}\n"
    )
lines.append("\n")
lines.append("■ 解釈\n")
lines.append("  ・診断系CTA（ブランド診断/気軽に診断）はペルソナLP誘導より心理的ハードルが低い\n")
lines.append("  ・CTAの違いをCPA比較で定量評価することで、今後のクリエイティブ制作優先度が変わる\n")
lines.append("\n")

# ── セクション3: メディア種別分析 ──
lines.append("【3. メディア種別 CPA 分析（Bootstrap 95%CI）】\n")
lines.append("メディア  広告数  CV    消化            CPA（95%CI）\n")
lines.append("─" * 90 + "\n")
for mt in media_types:
    st = media_stats.get(mt)
    if not st or st['n_ads'] == 0: continue
    lines.append(
        f"{mt:<8}  {st['n_ads']:>4}件  {st['cv']:>4.0f}  {fy(st['spend']):>12}  {fb(st)}\n"
    )
lines.append("\n")
lines.append("■ 解釈（推定:★★）\n")
lines.append("  ・静止画と動画でCPAに差がある場合、メディア選択戦略の見直しを検討\n")
lines.append("  ・制作コスト（静止画<動画）を考慮すると、静止画が競争力を持つ可能性あり\n")
lines.append("\n")

# ── セクション4: 週次トレンド分析 ──
lines.append("【4. 週次トレンド分析（線形回帰）】\n")
lines.append("週            消化            LINE_CV  CPA           CVR      CTR\n")
lines.append("─" * 90 + "\n")
for wr in week_rows:
    lines.append(
        f"{str(wr['week_start']):<12}  {fy(float(wr['spend'])):>12}  {float(wr['line_cv'] or 0):>7.0f}  "
        f"{fy(float(wr['cpa'])) if wr['cpa'] else '—':>12}  "
        f"{fp(float(wr['cvr'])) if wr['cvr'] else '—':>7}  "
        f"{fp(float(wr['ctr'])) if wr['ctr'] else '—':>7}\n"
    )
lines.append("\n")
lines.append("■ 線形回帰サマリー（直近90日 週単位）\n")

def reg_summary(reg, label, unit):
    if reg['slope'] is None:
        return f"  {label}: データ不足\n"
    trend = '改善傾向' if reg['slope'] < 0 else '悪化傾向'
    if label == 'CVR':
        trend = '改善傾向' if reg['slope'] > 0 else '悪化傾向'
    if label == 'CTR':
        trend = '改善傾向' if reg['slope'] > 0 else '悪化傾向'
    r2 = f"{reg['r2']:.3f}" if reg['r2'] is not None else '—'
    return f"  {label}: slope={reg['slope']:+.4f}{unit}/週  R²={r2}  → {trend}\n"

lines.append(reg_summary(reg_cpa, 'CPA', '円'))
lines.append(reg_summary(reg_cvr, 'CVR', ''))
lines.append(reg_summary(reg_ctr, 'CTR', ''))
lines.append("\n")
if reg_cpa['r2'] and reg_cpa['r2'] < 0.2:
    lines.append("  ※ CPA週次変動のR²が低い（<0.2）: 線形トレンドより週ごとのボラティリティが大きい。単週の値を過信しないこと\n")
lines.append("\n")

# ── セクション5: クリエイティブライフサイクル ──
lines.append("【5. クリエイティブライフサイクル分析】\n")
lines.append("フェーズ        広告数  CV    消化            CPA（95%CI）\n")
lines.append("─" * 90 + "\n")
for phase, st in life_stats.items():
    lines.append(
        f"{phase:<14}  {st['n']:>4}件  {st['cv']:>4.0f}  {fy(st['spend']):>12}  {fb(st)}\n"
    )
lines.append("\n")
if reg_age['slope'] is not None:
    r2_age = f"{reg_age['r2']:.3f}" if reg_age['r2'] is not None else '—'
    lines.append(f"■ 広告年齢 vs CPA 線形回帰: slope={reg_age['slope']:+.1f}円/日  R²={r2_age}\n")
    if reg_age['slope'] > 50:
        lines.append("  →「クリエイティブ疲弊」傾向あり（運用日数が増えるほどCPAが上昇）。定期的な入れ替えを推奨（推定:★★）\n")
    elif reg_age['slope'] < -50:
        lines.append("  →「学習効果」傾向あり（運用日数が増えるほどCPAが改善）。長期配信の継続を検討（推定:★★）\n")
    else:
        lines.append("  →「年齢 vs CPA」の関係は弱い（slope小）。疲弊・学習効果ともに現時点では不明（推定:★）\n")
lines.append("\n")

# ── セクション6: 季節変数フィット検証 ──
lines.append("【6. 季節変数 フィット検証（9月推奨 vs 実績）】\n")
lines.append("訴求軸    推奨比率  実績比率  差分      評価\n")
lines.append("─" * 70 + "\n")
for ax in ['タイパ', '単願', '併願']:
    rec  = SEASONAL_RECOMMENDED[ax]
    act  = actual_dist.get(ax, 0)
    diff = act - rec
    if abs(diff) <= 0.05:
        judge = '良好（±5%以内）'
    elif diff > 0:
        judge = f'過多（推奨より{diff:.0%}超過）'
    else:
        judge = f'不足（推奨より{abs(diff):.0%}不足）'
    lines.append(f"{ax:<6}    {rec*100:.0f}%      {act*100:.1f}%    {diff:+.1f}%    {judge}\n")
lines.append("\n")
lines.append("■ 推奨CTA（9月）: ブランド診断 / 気軽に診断\n")
lines.append("■ NGフレーズ（9月）: 「夏期講習で稼ぐ」「春から始めよう」「過度な緊急感」\n")
lines.append("■ 推奨フレーム: 「秋から安定的に稼ぎたい」「学年の切り替わりに向けて準備」\n")
lines.append("\n")

# ── セクション7: 推奨アクション ──
lines.append("【7. 推奨アクション（優先度順）】\n")
lines.append("\n")

# 最良訴求軸の特定
best_axis_name = best_ax[0]
best_cpa = best_ax[1].get('cpa') if best_ax[1] else None
worst_spend_zero = sorted(worst_zero, key=lambda r: r['spend'], reverse=True)

lines.append("① 【即時・最優先】不振クリエイティブの停止\n")
lines.append(f"   → spend≥1万円でCV=0の広告が{len(worst_zero)}件。即時停止して予算を勝ちクリエイティブに集中。\n")
if worst_spend_zero:
    top3 = worst_spend_zero[:3]
    for r in top3:
        lines.append(f"   停止候補: {r['ad_name'][:55]} ({fy(r['spend'])} / CV=0)\n")
lines.append("\n")

lines.append(f"② 【今週中】{best_axis_name}訴求の横展開\n")
lines.append(f"   → {best_axis_name}訴求が最良CPA {fy(best_cpa)}（Bootstrap 95%CI確認済み）。\n")
lines.append(f"   → 1シーズン5本目安に向け{best_axis_name}クリエイティブを追加制作。\n")
lines.append("   → 静止画でもCVが出ている事実を踏まえ、制作コスト削減も検討。\n")
lines.append("\n")

lines.append("③ 【今月中】季節変数ポートフォリオを9月推奨に調整\n")
for ax in ['タイパ', '単願', '併願']:
    rec = SEASONAL_RECOMMENDED[ax]
    act = actual_dist.get(ax, 0)
    diff = act - rec
    if abs(diff) > 0.05:
        direction = '予算削減' if diff > 0 else '予算増加'
        lines.append(f"   → {ax}: 現在{act*100:.1f}% → 推奨{rec*100:.0f}%（{direction}が必要）\n")
lines.append("\n")

lines.append("④ 【次期施策】週次トレンドのモニタリング強化\n")
if reg_cpa['slope'] and reg_cpa['slope'] > 0:
    lines.append(f"   → CPA週次slope={reg_cpa['slope']:+.0f}円/週（悪化傾向）。オーディエンス疲弊の可能性。\n")
    lines.append("   → 新規クリエイティブの投入タイミングを前倒し検討。\n")
else:
    lines.append(f"   → CPA週次slope={reg_cpa['slope']:+.0f}円/週（改善傾向）。引き続きモニタリング継続。\n")
lines.append("\n")

lines.append("⑤ 【計測環境改善】管理画面とBQの乖離を定期確認\n")
lines.append("   → custom_cv_2（応募CV）がLINE登録CVと同値になるバグは継続中。\n")
lines.append("   → 応募数は手動入力で対応。月次でBQ値と管理画面の実数を照合すること。\n")
lines.append("\n")
lines.append("─" * 80 + "\n")
lines.append("証拠強度: ★★★=BQデータ実績  ★★=複数観察一致  ★=論理的推測\n")
lines.append("Bootstrap CI: 2000回リサンプリング。CI幅が広い場合はサンプル不足に注意。\n")

full_text = "".join(lines)

# ── Google Doc作成 ─────────────────────────────────────────────────
print("\nGoogle Docを作成中...")
doc = docs_svc.documents().create(body={
    "title": f"ST Meta広告 深掘り分析レポート（直近90日・{today}）"
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

# スタイル適用
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
