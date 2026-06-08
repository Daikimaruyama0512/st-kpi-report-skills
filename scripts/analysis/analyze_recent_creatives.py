# scripts/analyze_recent_creatives.py
# 直近1ヶ月のSTクリエイティブ分析（create-scenario skill更新用）
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow google-auth
#
# 使い方: python3 scripts/analyze_recent_creatives.py

import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

TOKEN_FILE = "/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
PROJECT_ID = "bigquery-jukust"
BQ_VIEW    = "bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report"

SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
]

def run_query(client, query):
    return list(client.query(query).result())

def main():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    client = bigquery.Client(project=PROJECT_ID, credentials=creds)

    # ===== 1. 全体サマリー（直近30日）=====
    summary_query = f"""
WITH agg AS (
  SELECT
    COUNT(DISTINCT ad_name) AS ad_count,
    SUM(spend)                 AS total_spend,
    SUM(complete_registration) AS total_cv,
    SUM(link_clicks)           AS total_clicks,
    MIN(target_date)           AS date_from,
    MAX(target_date)           AS date_to
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    AND spend > 0
)
SELECT * FROM agg
"""
    rows = run_query(client, summary_query)
    r = rows[0]
    print("=== 全体サマリー（直近30日）===")
    print(f"期間: {r['date_from']} 〜 {r['date_to']}")
    print(f"広告数: {r['ad_count']}")
    print(f"総spend: {int(r['total_spend'] or 0):,}円")
    print(f"総CV: {int(r['total_cv'] or 0)}件")
    total_spend = float(r['total_spend'] or 0)
    total_cv    = float(r['total_cv'] or 0)
    print(f"全体CPA: {int(total_spend / total_cv) if total_cv > 0 else 'N/A'}円")
    print()

    # ===== 2. CTA別成果（直近30日・spend>=1万円）=====
    cta_query = f"""
WITH agg AS (
  SELECT
    ad_name,
    scenario,
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS cv,
    SUM(link_clicks)           AS link_clicks,
    SUM(impressions)           AS impressions
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY ad_name, scenario
)
SELECT
  ad_name,
  scenario,
  spend,
  cv,
  link_clicks,
  SAFE_DIVIDE(spend, NULLIF(cv, 0))          AS cpa,
  SAFE_DIVIDE(cv, NULLIF(link_clicks, 0))    AS cvr,
  SAFE_DIVIDE(spend, NULLIF(impressions, 0)) * 1000 AS cpm,
  CHAR_LENGTH(IFNULL(scenario, ''))          AS scenario_len
FROM agg
WHERE spend >= 10000
ORDER BY cpa ASC
"""
    rows = run_query(client, cta_query)
    print(f"=== 広告別成果（spend>=1万円・CPA昇順） 件数: {len(rows)} ===")
    results = []
    for r in rows:
        cpa = float(r['cpa']) if r['cpa'] else 0
        cvr = float(r['cvr']) if r['cvr'] else 0
        results.append({
            'ad_name':      r['ad_name'],
            'scenario':     r['scenario'],
            'spend':        float(r['spend'] or 0),
            'cv':           float(r['cv'] or 0),
            'cpa':          cpa,
            'cvr':          round(cvr * 100, 2),
            'cpm':          round(float(r['cpm'] or 0), 0),
            'scenario_len': int(r['scenario_len'] or 0),
        })

    # CTA分類（シナリオテキストからキーワード抽出）
    def classify_cta(ad_name, scenario):
        text = (scenario or '') + ' ' + (ad_name or '')
        if 'ペルソナ' in text or 'juku.st/match' in text:
            return 'ペルソナLP'
        elif 'juku.st/search' in text or 'スカウト' in text:
            return 'ペルソナLP単願'
        elif 'ブランド診断' in text or 'brand' in text.lower():
            return 'ブランド診断'
        elif '気軽' in text or 'かんたん' in text or 'casual' in text.lower():
            return '気軽に診断'
        elif '3分' in text or '診断' in text:
            return '3分診断'
        elif 'LINE' in text and ('登録' in text or '追加' in text):
            return 'LINE登録'
        else:
            return 'その他/不明'

    # 訴求軸分類（ad_nameの命名規則から）
    def classify_appeal(ad_name):
        if not ad_name:
            return '不明'
        # 新命名規則: NV_X または EV_X (3文字目が訴求軸)
        import re
        m = re.match(r'^[NE][VPM]_([A-I])', ad_name)
        if m:
            axis = m.group(1)
            axis_map = {
                'A': '安心', 'B': '承認', 'C': '自己実現(タイパ)',
                'D': '所属', 'E': '潜在層', 'F': '企業PUSH',
                'G': '潜在層_3分診断', 'H': '潜在層_年収診断', 'I': 'プロ講師_3分診断'
            }
            return axis_map.get(axis, f'軸{axis}')
        # 旧命名規則
        if ad_name.startswith('01') or 'タイパ' in ad_name:
            return '推定:タイパ(旧)'
        elif ad_name.startswith('02') or '単願' in ad_name:
            return '推定:単願(旧)'
        elif ad_name.startswith('03') or '併願' in ad_name:
            return '推定:併願(旧)'
        return '旧命名/不明'

    # 動画の型分類
    def classify_video_type(ad_name):
        if not ad_name:
            return '不明'
        import re
        m = re.match(r'^[NE][VPM]_[A-I](\d{2})', ad_name)
        if m:
            t = m.group(1)
            type_map = {
                '01': 'UGC', '02': 'インタビュー', '03': '中の人',
                '04': 'ビジネスライク', '05': 'アニメ',
                '06': 'UGC-強フック', '07': 'インタビューUGC風', '08': 'インタビュー漫画風'
            }
            return type_map.get(t, f'型{t}')
        return '旧命名/不明'

    for r in results:
        r['cta']        = classify_cta(r['ad_name'], r['scenario'])
        r['appeal']     = classify_appeal(r['ad_name'])
        r['video_type'] = classify_video_type(r['ad_name'])

    # CTA別集計
    from collections import defaultdict
    cta_agg = defaultdict(lambda: {'spend': 0, 'cv': 0, 'clicks': 0, 'count': 0})
    for r in results:
        c = cta_agg[r['cta']]
        c['spend'] += r['spend']
        c['cv']    += r['cv']
        c['count'] += 1

    print("\n=== CTA別集計 ===")
    cta_list = []
    for cta, c in cta_agg.items():
        cpa = int(c['spend'] / c['cv']) if c['cv'] > 0 else 99999
        cvr_str = ''
        cta_list.append({'cta': cta, 'cpa': cpa, 'spend': c['spend'], 'cv': c['cv'], 'count': c['count']})
    cta_list.sort(key=lambda x: x['cpa'])
    for c in cta_list:
        print(f"  {c['cta']}: CPA={c['cpa']:,}円  cv={int(c['cv'])}件  spend={int(c['spend']):,}円  n={c['count']}")

    # 訴求軸別集計
    appeal_agg = defaultdict(lambda: {'spend': 0, 'cv': 0, 'count': 0})
    for r in results:
        a = appeal_agg[r['appeal']]
        a['spend'] += r['spend']
        a['cv']    += r['cv']
        a['count'] += 1

    print("\n=== 訴求軸別集計 ===")
    appeal_list = []
    for appeal, a in appeal_agg.items():
        cpa = int(a['spend'] / a['cv']) if a['cv'] > 0 else 99999
        appeal_list.append({'appeal': appeal, 'cpa': cpa, 'spend': a['spend'], 'cv': a['cv'], 'count': a['count']})
    appeal_list.sort(key=lambda x: x['cpa'])
    for a in appeal_list:
        print(f"  {a['appeal']}: CPA={a['cpa']:,}円  cv={int(a['cv'])}件  spend={int(a['spend']):,}円  n={a['count']}")

    # 動画の型別集計
    vtype_agg = defaultdict(lambda: {'spend': 0, 'cv': 0, 'count': 0})
    for r in results:
        v = vtype_agg[r['video_type']]
        v['spend'] += r['spend']
        v['cv']    += r['cv']
        v['count'] += 1

    print("\n=== 動画の型別集計 ===")
    vtype_list = []
    for vtype, v in vtype_agg.items():
        cpa = int(v['spend'] / v['cv']) if v['cv'] > 0 else 99999
        vtype_list.append({'type': vtype, 'cpa': cpa, 'spend': v['spend'], 'cv': v['cv'], 'count': v['count']})
    vtype_list.sort(key=lambda x: x['cpa'])
    for v in vtype_list:
        print(f"  {v['type']}: CPA={v['cpa']:,}円  cv={int(v['cv'])}件  spend={int(v['spend']):,}円  n={v['count']}")

    # シナリオ文字数帯別集計
    print("\n=== シナリオ字数帯別成果 ===")
    len_agg = defaultdict(lambda: {'spend': 0, 'cv': 0, 'count': 0, 'total_len': 0})
    for r in results:
        slen = r['scenario_len']
        if slen == 0:
            band = 'シナリオなし'
        elif slen <= 150:
            band = '〜150字'
        elif slen <= 200:
            band = '151〜200字'
        elif slen <= 250:
            band = '201〜250字'
        else:
            band = '251字〜'
        b = len_agg[band]
        b['spend']     += r['spend']
        b['cv']        += r['cv']
        b['count']     += 1
        b['total_len'] += slen

    for band in ['〜150字', '151〜200字', '201〜250字', '251字〜', 'シナリオなし']:
        if band in len_agg:
            b = len_agg[band]
            cpa = int(b['spend'] / b['cv']) if b['cv'] > 0 else 99999
            avg_len = int(b['total_len'] / b['count']) if b['count'] > 0 else 0
            print(f"  {band}（平均{avg_len}字）: CPA={cpa:,}円  cv={int(b['cv'])}件  n={b['count']}")

    # ===== 3. 動画エンゲージメント（直近30日・spend>=1万円）=====
    engage_query = f"""
WITH agg AS (
  SELECT
    ad_name,
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS cv,
    SUM(impressions)           AS impressions,
    SUM(video_view_3s)         AS v3s,
    SUM(video_p25)             AS p25,
    SUM(video_p50)             AS p50,
    SUM(video_p75)             AS p75,
    SUM(video_p100)            AS p100
  FROM `{BQ_VIEW}`
  WHERE target_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY ad_name
),
avg_rates AS (
  SELECT
    AVG(SAFE_DIVIDE(v3s, NULLIF(impressions,0)))  AS avg_3s,
    AVG(SAFE_DIVIDE(p100, NULLIF(impressions,0))) AS avg_p100
  FROM agg
  WHERE spend >= 10000
)
SELECT
  a.ad_name,
  a.spend,
  a.cv,
  SAFE_DIVIDE(a.spend, NULLIF(a.cv, 0))            AS cpa,
  SAFE_DIVIDE(a.v3s,   NULLIF(a.impressions, 0))   AS rate_3s,
  SAFE_DIVIDE(a.p100,  NULLIF(a.impressions, 0))   AS rate_100,
  r.avg_3s,
  r.avg_p100,
  CASE
    WHEN SAFE_DIVIDE(a.v3s, NULLIF(a.impressions,0)) >= r.avg_3s
     AND SAFE_DIVIDE(a.p100, NULLIF(a.impressions,0)) >= r.avg_p100
    THEN 'テンポ良好'
    ELSE 'テンポ不良'
  END AS tempo
FROM agg a, avg_rates r
WHERE a.spend >= 10000
"""
    rows = run_query(client, engage_query)

    tempo_agg = defaultdict(lambda: {'spend': 0, 'cv': 0, 'count': 0, 'sum_3s': 0.0, 'sum_100': 0.0})
    for r in rows:
        t = r['tempo']
        ta = tempo_agg[t]
        ta['spend'] += float(r['spend'] or 0)
        ta['cv']    += float(r['cv'] or 0)
        ta['count'] += 1
        ta['sum_3s']  += float(r['rate_3s'] or 0)
        ta['sum_100'] += float(r['rate_100'] or 0)

    print("\n=== テンポ（エンゲージメント）別成果 ===")
    for tempo in ['テンポ良好', 'テンポ不良']:
        if tempo in tempo_agg:
            ta = tempo_agg[tempo]
            cpa = int(ta['spend'] / ta['cv']) if ta['cv'] > 0 else 99999
            avg_3s  = round(ta['sum_3s']  / ta['count'] * 100, 1) if ta['count'] > 0 else 0
            avg_100 = round(ta['sum_100'] / ta['count'] * 100, 1) if ta['count'] > 0 else 0
            print(f"  {tempo}: CPA={cpa:,}円  cv={int(ta['cv'])}件  3秒再生率={avg_3s}%  完了率={avg_100}%  n={ta['count']}")

    # ===== 4. TOP10広告（CPA昇順）=====
    print("\n=== TOP10広告（CPA昇順・直近30日）===")
    for i, r in enumerate(results[:10]):
        print(f"  {i+1}. {r['ad_name']}")
        print(f"     訴求={r['appeal']}  型={r['video_type']}  CTA={r['cta']}")
        print(f"     CPA={int(r['cpa']):,}円  CVR={r['cvr']}%  spend={int(r['spend']):,}円  cv={int(r['cv'])}")
        if r['scenario']:
            print(f"     シナリオ冒頭: {r['scenario'][:50]}...")
        print()

    # JSON保存
    output = {
        'summary': {
            'date_from': str(rows[0]['avg_3s']) if rows else '',  # placeholder
            'total_spend': total_spend,
            'total_cv': total_cv,
        },
        'cta': cta_list,
        'appeal': appeal_list,
        'vtype': vtype_list,
        'top10': results[:10],
    }
    with open('/Users/119322/Desktop/claude-code-template_af/scripts/data/recent_creative_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print("=== JSON保存: scripts/data/recent_creative_analysis.json ===")

if __name__ == '__main__':
    main()
