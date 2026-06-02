#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毎週月曜 9:00 JST（0:00 UTC）に実行するローカル cron スクリプト。
ST Meta広告の直近90日BQデータ + 季節変数カレンダーを元に
knowledge/creative_trend_insights.md を自動更新し git push する。

必要: pip install google-cloud-bigquery db-dtypes pyarrow pandas google-auth google-auth-httplib2
crontab: 0 0 * * 1 cd /Users/119322/claude-code-template_af && /usr/bin/python3 scripts/update_seasonal_insights.py >> /tmp/st_weekly_update.log 2>&1
"""

import sys
import io
import os
import re
import json
import subprocess
from datetime import date, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

# ===== 定数 =====
REPO_DIR      = "/Users/119322/claude-code-template_af"
TOKEN_FILE    = r"/Users/119322/claude-code-template_af/secrets/token.json"
CACHE_FILE    = r"/Users/119322/claude-code-template_af/scripts/weekly_bq_cache.json"
CALENDAR_FILE = "/Users/119322/claude-code-template_af/knowledge/Prerequisites/ST_05_大学生カレンダー.md"
OUTPUT_FILE   = "/Users/119322/claude-code-template_af/knowledge/creative_trend_insights.md"
PROJECT_ID    = "bigquery-jukust"
SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

# 旧命名規則セグメントマップ
OLD_SEGMENT_MAP = [
    (r'^01タイパ|^01_?タイパ',     'タイパ重視層（C:自己実現）'),
    (r'^02単願|^02_?単願',         '単願型（A/B:安心/承認）'),
    (r'^03併願|^03_?併願',         '併願型（E:潜在層）'),
    (r'^App|^app',                 'アプリ訴求'),
    (r'^ASC',                      'ASC（自動最適化）'),
]

AD_NAME_CTA_MAP = [
    ('ペルソナLP',   r'ペルソナLP|ペルソナlp'),
    ('ブランド診断', r'ブランド診断'),
    ('気軽に診断',   r'気軽に診断'),
    ('3分診断',      r'3分.?診断'),
    ('16タイプ診断', r'16タイプ診断'),
    ('LP',           r'^LP$'),
]

CTA_PATTERNS = [
    ('ブランド診断', r'ブランド診断'),
    ('3分診断', r'3分.{0,5}診断|三分.{0,5}診断'),
    ('年収診断', r'年収.{0,5}診断'),
    ('16タイプ診断', r'16タイプ診断|16.{0,5}タイプ'),
    ('適職診断', r'適職診断'),
    ('気軽に診断', r'気軽に.{0,5}診断'),
    ('診断して', r'診断し(て|よう|てね|てみよう|ください)|診断はこちら'),
    ('LINE登録', r'LINE.{0,10}(登録|追加)(し(て|よう))?'),
    ('ペルソナLP', r'ペルソナ|詳しくはこちら|求人.{0,5}(見|探)'),
]

NAMING_RE = re.compile(r'^([NE])([VPM])_([A-I])(\d{2})(\d{2})(\d)_(\d{6})')


# ===== 認証 =====
def get_credentials():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


# ===== キャッシュ管理 =====
def load_cache():
    """当日のキャッシュがあればDataFrameを返す、なければNone"""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        if cache.get('fetched_at') == date.today().isoformat():
            df = pd.DataFrame(cache['data'])
            print(f"キャッシュ読み込み: {len(df)} 件（当日キャッシュ・BQクエリスキップ）")
            return df
    except Exception as e:
        print(f"キャッシュ読み込みエラー: {e}", file=sys.stderr)
    return None


def save_cache(df):
    """DataFrameをJSONキャッシュに保存"""
    try:
        records = df.where(df.notna(), other=None).to_dict(orient='records')
        cache = {'fetched_at': date.today().isoformat(), 'data': records}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"キャッシュ保存: {CACHE_FILE}")
    except Exception as e:
        print(f"キャッシュ保存エラー: {e}", file=sys.stderr)


# ===== BigQuery: 90日広告別集計 =====
def fetch_bq_data(client):
    query = """
WITH agg AS (
  SELECT
    ad_name,
    ANY_VALUE(scenario)         AS scenario,
    SUM(spend)                  AS spend,
    SUM(complete_registration)  AS cv,
    SUM(link_clicks)            AS link_clicks,
    SUM(impressions)            AS impressions,
    SUM(video_view_3s)          AS video_view_3s,
    SUM(video_p25)              AS video_p25,
    SUM(video_p50)              AS video_p50,
    SUM(video_p75)              AS video_p75,
    SUM(video_p100)             AS video_p100
  FROM `bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report`
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
  GROUP BY ad_name
)
SELECT
  ad_name,
  scenario,
  spend,
  cv,
  link_clicks,
  impressions,
  video_view_3s,
  video_p25,
  video_p50,
  video_p75,
  video_p100,
  SAFE_DIVIDE(spend, cv)                   AS cpa,
  SAFE_DIVIDE(cv, link_clicks)             AS cvr,
  SAFE_DIVIDE(video_view_3s, impressions)  AS rate_3s,
  SAFE_DIVIDE(video_p25, impressions)      AS rate_p25,
  SAFE_DIVIDE(video_p50, impressions)      AS rate_p50,
  SAFE_DIVIDE(video_p75, impressions)      AS rate_p75,
  SAFE_DIVIDE(video_p100, impressions)     AS rate_p100
FROM agg
WHERE spend >= 10000
ORDER BY cpa ASC NULLS LAST
"""
    print("BigQuery クエリ実行中...")
    df = client.query(query).to_dataframe()
    print(f"BigQuery取得: {len(df)} 件（spend>=1万円）")
    return df


# ===== 命名規則パース =====
def parse_old_segment(ad_name):
    for pattern, label in OLD_SEGMENT_MAP:
        if re.search(pattern, str(ad_name)):
            return label
    return '不明（旧命名）'

def parse_ad_name_cta(ad_name):
    parts = str(ad_name).split('_')
    candidates = parts[1:] if len(parts) > 1 else []
    for part in candidates:
        for label, pattern in AD_NAME_CTA_MAP:
            if re.search(pattern, part.strip()):
                return label
    return None

def parse_ad_name(ad_name):
    m = NAMING_RE.match(str(ad_name))
    if m:
        return {
            'appeal': m.group(3) + ':自己実現' if m.group(3) == 'C' else m.group(3),
            'cta_from_name': None,
            'is_new': True,
        }
    return {
        'appeal': parse_old_segment(ad_name),
        'cta_from_name': parse_ad_name_cta(ad_name),
        'is_new': False,
    }

def extract_cta_from_scenario(text):
    if not text or not str(text).strip():
        return None
    for label, pattern in CTA_PATTERNS:
        if re.search(pattern, str(text)):
            return label
    return 'その他'

def enrich_df(df):
    """セグメント・CTA・文字数帯カラムを付与"""
    parsed = df['ad_name'].apply(parse_ad_name)
    df['appeal']       = parsed.apply(lambda x: x['appeal'])
    df['cta_from_name'] = parsed.apply(lambda x: x['cta_from_name'])
    df['scenario_filled'] = df['scenario'].apply(lambda x: str(x).strip() if x else '')

    def get_cta(row):
        if row['cta_from_name']:
            return row['cta_from_name']
        result = extract_cta_from_scenario(row['scenario_filled'])
        return result if result else '(シナリオなし)'

    df['cta_type']    = df.apply(get_cta, axis=1)
    df['scenario_len'] = df['scenario_filled'].apply(len)

    def char_band(n):
        if n == 0: return '0:シナリオなし'
        if n <= 200: return '1:1-200字'
        if n <= 400: return '2:201-400字'
        return '3:401字以上'

    df['char_band'] = df['scenario_len'].apply(char_band)
    return df


# ===== 分析関数（簡略版） =====
def fmt_yen(v):
    try:
        if v != v: return '-'
        return f"{int(v):,}"
    except Exception:
        return '-'

def fmt_pct(v, digits=1):
    try:
        if v != v: return '-'
        return f"{v:.{digits}f}%"
    except Exception:
        return '-'


def analyze_cta_simple(df):
    result = df.groupby('cta_type').agg(
        spend=('spend', 'sum'),
        cv=('cv', 'sum'),
        link_clicks=('link_clicks', 'sum'),
        ad_count=('ad_name', 'count'),
    ).reset_index()
    result['cpa'] = result['spend'] / result['cv'].replace(0, float('nan'))
    result['cvr_pct'] = result['cv'] / result['link_clicks'].replace(0, float('nan')) * 100
    return result.sort_values('cpa')


def analyze_appeal_simple(df):
    result = df.groupby('appeal').agg(
        spend=('spend', 'sum'),
        cv=('cv', 'sum'),
        link_clicks=('link_clicks', 'sum'),
        ad_count=('ad_name', 'count'),
    ).reset_index()
    result['cpa'] = result['spend'] / result['cv'].replace(0, float('nan'))
    result['cvr_pct'] = result['cv'] / result['link_clicks'].replace(0, float('nan')) * 100
    return result.sort_values('cpa')


def analyze_char_band_simple(df):
    result = df.groupby('char_band').agg(
        spend=('spend', 'sum'),
        cv=('cv', 'sum'),
        link_clicks=('link_clicks', 'sum'),
        ad_count=('ad_name', 'count'),
        avg_len=('scenario_len', 'mean'),
    ).reset_index()
    result['cpa'] = result['spend'] / result['cv'].replace(0, float('nan'))
    result['cvr_pct'] = result['cv'] / result['link_clicks'].replace(0, float('nan')) * 100
    return result.sort_values('char_band')


def analyze_tempo_simple(df):
    vdf = df[df['video_view_3s'] > 0].copy()
    if vdf.empty:
        return pd.DataFrame()

    total_imp = vdf['impressions'].sum()
    avg_3s  = vdf['video_view_3s'].sum() / total_imp
    avg_p25 = vdf['video_p25'].sum()     / total_imp
    avg_p50 = vdf['video_p50'].sum()     / total_imp
    avg_p75 = vdf['video_p75'].sum()     / total_imp
    avg_p100= vdf['video_p100'].sum()    / total_imp

    vdf['tempo_good'] = (
        (vdf['rate_3s']   >= avg_3s)  &
        (vdf['rate_p25']  >= avg_p25) &
        (vdf['rate_p50']  >= avg_p50) &
        (vdf['rate_p75']  >= avg_p75) &
        (vdf['rate_p100'] >= avg_p100)
    )
    vdf['tempo_label'] = vdf['tempo_good'].map({True: 'テンポ良好群', False: 'テンポ不良群'})

    result = vdf.groupby('tempo_label').agg(
        spend=('spend', 'sum'),
        cv=('cv', 'sum'),
        link_clicks=('link_clicks', 'sum'),
        ad_count=('ad_name', 'count'),
        avg_rate_3s=('rate_3s', 'mean'),
        avg_rate_p100=('rate_p100', 'mean'),
    ).reset_index()
    result['cpa'] = result['spend'] / result['cv'].replace(0, float('nan'))
    result['cvr_pct'] = result['cv'] / result['link_clicks'].replace(0, float('nan')) * 100
    return result.sort_values('cpa')


# ===== 季節変数: カレンダーMDを解析 =====
MONTH_JP = ['', '1月', '2月', '3月', '4月', '5月', '6月',
             '7月', '8月', '9月', '10月', '11月', '12月']

# 月→出稿強度（「広告出稿メリハリガイド」より）
INTENSITY_MAP = {
    1: '△ 維持〜仕込み', 2: '△ 維持〜仕込み',
    3: '◎ 強化（新1年生 ペルソナLP中心）', 4: '◎ 強化（新入生・春休み刈り取り）',
    5: '○ 通常〜強化', 6: '○ 通常〜強化',
    7: '◎ 強化（夏期講習）', 8: '◎ 強化（夏期講習 繁忙期）',
    9: '○ 通常（2学期スタート）',
    10: '△ 維持', 11: '○ 強化（冬期講習需要）', 12: '○ 強化（冬期講習需要）',
}

# 月→推奨CTA（「CTA別の時期推奨」より）
CTA_SEASON_MAP = {
    1: '気軽に診断（潜在リスト仕込み）',
    2: '気軽に診断（潜在リスト仕込み）',
    3: 'ペルソナLP + 新1年生向け',
    4: 'ペルソナLP + 新1年生向け',
    5: '塾ブランド診断 + 気軽に診断',
    6: '塾ブランド診断 + 気軽に診断',
    7: 'ペルソナLP + 塾ブランド診断',
    8: 'ペルソナLP + 塾ブランド診断',
    9: '塾ブランド診断 + 気軽に診断',
    10: '塾ブランド診断 + 気軽に診断',
    11: '塾ブランド診断 + ペルソナLP',
    12: '塾ブランド診断 + ペルソナLP',
}

# 月→シナリオ注意点
SCENARIO_NOTES_MAP = {
    1:  ['テスト期間中は反応が鈍い。押しつけ感のある訴求を避け「気軽に見てみて」で潜在リストを仕込む',
         '3月の刈り取りに向けて「春から始める」系フックを仕込んでおく'],
    2:  ['春の採用ピークを見越した「先行登録」訴求が有効',
         '受験経験を活かせる塾バイトへの共感フックを入れる'],
    3:  ['新大学1年生の初バイト探しが最大ピーク。「初めてでも安心」「受験経験をお金に換える」フックが最刺さり',
         '即決層が多いのでペルソナLP直誘導を最優先。タイパ系FOMOより「確実な一歩」訴求が合う'],
    4:  ['新入生が大学生活に慣れ始める時期。「大学と両立できる塾バイト」の差別化訴求',
         '春休み終わりの焦りを活用した「今始めれば夏までに慣れる」フックも有効'],
    5:  ['GW明けの多忙感より「時間の融通が利く」という差別化を前面に',
         '前期テスト対策需要が高まる時期。「テスト前の繁忙期に向けて今登録を」というFOMO訴求が有効'],
    6:  ['前期中間テスト需要ピーク。「高時給・テスト期間に稼ぐ」直接訴求が効く',
         '「今が繁忙期＝高時給案件が多い」という希少性フックを冒頭0.5秒に入れる'],
    7:  ['夏期講習の大繁忙期直前。「夏前に登録しないと優良枠が埋まる」損失回避フックが最強',
         'ペルソナLP直応募で即決層を刈り取る。まとまった収入を具体的な数字で示す'],
    8:  ['最大繁忙期。「夏期講習フル稼働でXX万円」の実績数字ベースシナリオが刺さる',
         '既登録者の紹介・口コミ型UGC動画が信頼感を高めて効果的'],
    9:  ['2学期スタート。「新生活に合わせた安定収入」訴求。秋からでも間に合う安心感',
         'サークル・学祭と掛け持ち可能な柔軟性訴求が差別化ポイント'],
    10: ['学祭・サークルシーズンで反応が鈍い。継続配信で存在感を保つ維持フェーズ',
         '11月冬期講習需要に向けた仕込みとして「事務給・高時給」訴求を早めに入れる'],
    11: ['冬期講習需要急増。「年末・クリスマスに稼ぐ」損失回避＋タイパ訴求の組み合わせ',
         '「事務給」「交通費全額支給」など待遇面の具体的数字が刺さる時期'],
    12: ['年末・クリスマスの出費を意識した「損しないバイト選び」訴求',
         '新年に向けた「来年のために今仕込む」フォワードルッキングフックも有効'],
}


def get_seasonal_vars(month: int) -> dict:
    """月から季節変数を返す（カレンダーMDを使わずハードコード版）"""
    # 需要スコアと心理フェーズ・訴求テーマ（ST_05_大学生カレンダー.md より）
    data = {
        1:  {'score': 3, 'stars': '★★★☆☆', 'phase': '逃避期',
             'theme': 'テスト勉強の合間に診断・気軽に探す'},
        2:  {'score': 4, 'stars': '★★★★☆', 'phase': '焦燥期',
             'theme': '受験知識を活かす・春に向けて準備'},
        3:  {'score': 5, 'stars': '★★★★★', 'phase': '新生活期（最大）',
             'theme': '新1年生の初バイト・受験経験換金・春休みに稼ぐ'},
        4:  {'score': 4, 'stars': '★★★★☆', 'phase': '新生活期',
             'theme': 'スタートダッシュ・大学と両立できる塾バイト'},
        5:  {'score': 4, 'stars': '★★★★☆', 'phase': '安定期→テスト準備',
             'theme': 'GW明けに備えて・テスト対策のニーズ高まる'},
        6:  {'score': 4, 'stars': '★★★★☆', 'phase': 'テスト需要期',
             'theme': '「テスト前の今が繁忙期」需要高まる・高時給案件増加'},
        7:  {'score': 5, 'stars': '★★★★★', 'phase': '繁忙期準備',
             'theme': '夏期講習で稼ぐ・夏前に登録しておく'},
        8:  {'score': 5, 'stars': '★★★★★', 'phase': '繁忙期',
             'theme': '夏期講習フル稼働・まとまった金額を稼げる'},
        9:  {'score': 4, 'stars': '★★★★☆', 'phase': '新学期期',
             'theme': '秋から始める・2学期に向けた収入源確保'},
        10: {'score': 3, 'stars': '★★★☆☆', 'phase': '安定期',
             'theme': '継続訴求・安定したシフト'},
        11: {'score': 4, 'stars': '★★★★☆', 'phase': '実利期',
             'theme': '冬期講習で稼ぐ・事務給・高時給'},
        12: {'score': 4, 'stars': '★★★★☆', 'phase': '防衛期',
             'theme': '年末に稼ぐ・事務給の確認・損しないバイト選び'},
    }
    d = data[month]
    return {
        'score_str': d['stars'] + f"（{d['score']}/5）",
        'phase': d['phase'],
        'theme': d['theme'],
        'cta': CTA_SEASON_MAP[month],
        'intensity': INTENSITY_MAP[month],
        'notes': SCENARIO_NOTES_MAP[month],
    }


# ===== MDファイル生成 =====
def build_seasonal_section(month: int, today_str: str) -> str:
    v = get_seasonal_vars(month)
    notes_md = '\n'.join(f'- {n}' for n in v['notes'])
    return f"""## 今週の季節変数（{today_str} 更新）

- **今月（{month}月）の需要スコア**: {v['score_str']}
- **心理フェーズ**: {v['phase']}
- **主な訴求テーマ**: {v['theme']}
- **推奨CTA**: {v['cta']}
- **出稿強度**: {v['intensity']}

### シナリオ作成時の季節的注意点
{notes_md}"""


def build_cta_section(cta_df: pd.DataFrame) -> str:
    rows = []
    for _, r in cta_df.iterrows():
        cpa_str = fmt_yen(r['cpa']) + '円' if r['cpa'] == r['cpa'] else '-'
        cvr_str = fmt_pct(r['cvr_pct'])
        rows.append(f"| {'**' + r['cta_type'] + '**' if r.name == cta_df.index[0] else r['cta_type']} "
                    f"| {cpa_str} | {cvr_str} | {int(r['ad_count'])} |")

    # 最良CTA
    valid = cta_df[cta_df['cv'] > 0]
    best = valid.iloc[0] if not valid.empty else None
    worst = valid.iloc[-1] if len(valid) > 1 else None

    hint_lines = []
    if best is not None:
        hint_lines.append(f"- {best['cta_type']}はCVRが最良。シナリオ作成時は{best['cta_type']}への誘導を第一候補とする")
    if worst is not None and best is not None and worst['cta_type'] != best['cta_type']:
        hint_lines.append(f"- {worst['cta_type']}はCPA・CVRが低位。積極採用は慎重に")
    hints = '\n'.join(hint_lines) if hint_lines else '- データ更新中'

    table = "| CTA | CPA | CVR | 広告数 |\n|---|---|---|---|\n" + '\n'.join(rows)
    return f"""## 1. CTA別成果（最重要）

{table}

**示唆:**
{hints}"""


def build_appeal_section(ap_df: pd.DataFrame) -> str:
    rows = []
    for i, (_, r) in enumerate(ap_df.iterrows()):
        bold = i == 0 and r['cv'] > 0
        label = f"**{r['appeal']}**" if bold else r['appeal']
        rows.append(f"| {label} | {fmt_yen(r['cpa'])}円 | {fmt_pct(r['cvr_pct'])} "
                    f"| {int(r['spend']):,}円 | {int(r['ad_count'])} |")

    valid = ap_df[ap_df['cv'] > 0]
    best = valid.iloc[0] if not valid.empty else None
    hint_lines = []
    if best is not None:
        hint_lines.append(f"- {best['appeal']}のCPA・CVRが最良。新規シナリオ作成時はこのセグメントを優先的に提案する")

    table = "| セグメント | CPA | CVR | spend | 広告数 |\n|---|---|---|---|---|\n" + '\n'.join(rows)
    hints = '\n'.join(hint_lines) if hint_lines else '- データ更新中'
    return f"""## 2. 訴求セグメント（訴求軸）別成果

{table}

**示唆:**
{hints}"""


def build_char_section(cb_df: pd.DataFrame) -> str:
    label_map = {
        '0:シナリオなし': 'シナリオなし',
        '1:1-200字': '1〜200字',
        '2:201-400字': '201〜400字',
        '3:401字以上': '401字以上',
    }
    rows = []
    best_row = None
    best_cpa = float('inf')
    for _, r in cb_df.iterrows():
        if r['char_band'] == '0:シナリオなし':
            continue
        label = label_map.get(r['char_band'], r['char_band'])
        avg_len = int(r['avg_len']) if r['avg_len'] == r['avg_len'] else 0
        cpa = r['cpa']
        if cpa == cpa and cpa < best_cpa and r['cv'] > 0:
            best_cpa = cpa
            best_row = r
        bold = (best_row is not None and r.equals(best_row))
        label_disp = f"**{label}**" if bold else label
        rows.append(f"| {label_disp} | {avg_len}字 | {fmt_yen(cpa)}円 | {fmt_pct(r['cvr_pct'])} |")

    # シナリオなし行を末尾に追加
    for _, r in cb_df.iterrows():
        if r['char_band'] == '0:シナリオなし':
            rows.append(f"| シナリオなし | - | {fmt_yen(r['cpa'])}円 | {fmt_pct(r['cvr_pct'])} |")

    hint = ''
    if best_row is not None:
        avg_len = int(best_row['avg_len']) if best_row['avg_len'] == best_row['avg_len'] else 0
        hint = f"- 字幕テキスト{avg_len}字前後の広告がCPA最良。1カットに詰め込まず端的なキーワードに絞る"

    table = "| 文字数帯 | 平均字数 | CPA | CVR |\n|---|---|---|---|\n" + '\n'.join(rows)
    return f"""## 3. シナリオ文字数別成果

{table}

**示唆:**
- BigQueryの`scenario`カラムに記録された字幕テキストの文字数ベース（ナレーション全文とは別）
{hint if hint else '- データ更新中'}
- 字幕は「キーワードのみ」に絞り、説明文は音声で補う設計を推奨"""


def build_tempo_section(tempo_df: pd.DataFrame) -> str:
    if tempo_df.empty:
        return """## 4. テンポ（動画エンゲージメント）別成果

動画データなし（今週は分析スキップ）"""

    rows = []
    for i, (_, r) in enumerate(tempo_df.iterrows()):
        bold = i == 0
        label = f"**{r['tempo_label']}**" if bold else r['tempo_label']
        rate_3s = fmt_pct(r.get('avg_rate_3s', float('nan')) * 100, digits=1)
        rate_p100 = fmt_pct(r.get('avg_rate_p100', float('nan')) * 100, digits=1)
        rows.append(f"| {label} | {fmt_yen(r['cpa'])}円 | {rate_3s} | {rate_p100} | {int(r['ad_count'])} |")

    table = "| 区分 | CPA | 3秒再生率 | 動画完了率 | 広告数 |\n|---|---|---|---|---|\n" + '\n'.join(rows)
    return f"""## 4. テンポ（動画エンゲージメント）別成果

{table}

良好群の判定基準: 3秒再生率・25%/50%/75%/100%視聴率が全て全体平均以上

**示唆:**
- 3秒再生率を上げるには冒頭0.5秒のフックが決定的。シナリオ設計でフックに最も時間をかける
- テンポ良好群は完了率も高い傾向。フックが強いと最後まで見てもらえる"""


def build_guideline_section(cta_df: pd.DataFrame, ap_df: pd.DataFrame) -> str:
    valid_cta = cta_df[cta_df['cv'] > 0]
    best_cta  = valid_cta.iloc[0]['cta_type'] if not valid_cta.empty else 'ペルソナLP'
    valid_ap  = ap_df[ap_df['cv'] > 0]
    best_ap   = valid_ap.iloc[0]['appeal'] if not valid_ap.empty else 'タイパ重視層'

    return f"""## シナリオ設計への適用ガイドライン

シナリオを出力する際は以下を必ず確認・反映する:

| 観点 | 実績からの推奨 | 優先度 |
|---|---|---|
| **CTA選択** | {best_cta}優先（直近90日CPA最良）→ 季節変数の推奨CTAも参照 | 最高 |
| **セグメント優先度** | {best_ap}（直近90日CPA最良）を優先 | 高 |
| **字幕文字量** | 1カット200字以内を意識。端的なキーワードに絞る | 高 |
| **フック設計** | 3秒再生率向上を目標。冒頭0.5秒を最優先で設計 | 最高 |
| **季節訴求** | 上記「今週の季節変数」セクションの注意点を必ず参照する | 最高 |"""


def build_md(today_str: str, month: int, period_start: str, period_end: str,
             df: pd.DataFrame,
             cta_df: pd.DataFrame, ap_df: pd.DataFrame,
             cb_df: pd.DataFrame, tempo_df: pd.DataFrame) -> str:
    total_ads   = len(df)
    total_spend = int(df['spend'].sum())
    total_cv    = int(df['cv'].sum())

    seasonal_sec  = build_seasonal_section(month, today_str)
    cta_sec       = build_cta_section(cta_df)
    appeal_sec    = build_appeal_section(ap_df)
    char_sec      = build_char_section(cb_df)
    tempo_sec     = build_tempo_section(tempo_df)
    guide_sec     = build_guideline_section(cta_df, ap_df)

    return f"""# STクリエイティブ傾向分析 インサイト

BigQuery直近90日データ（{today_str}時点）から導出した傾向。
シナリオ作成時にこのファイルの示唆を反映すること。

---

{seasonal_sec}

---

## 分析スコープ

- 対象: 塾講師ステーション（ST）Meta広告
- 期間: 直近90日（{period_start} 〜 {period_end}）
- 対象広告: spend ≥ 1万円（計{total_ads}広告・spend合計 約{total_spend // 10000}万円・CV合計 {total_cv}件）
- 主要KPI: LINE登録CV（complete_registration）

---

{cta_sec}

---

{appeal_sec}

---

{char_sec}

---

{tempo_sec}

---

{guide_sec}

---

## 分析方法・注意事項

- 分析スクリプト: `scripts/analyze_st_creatives.py`（詳細分析用）、`scripts/update_seasonal_insights.py`（週次自動更新）
- 字幕文字数はBigQuery `scenario`カラムの値。ナレーション全文と異なる可能性がある
- 旧命名規則広告（01タイパ/02単願/03併願 形式）のデータ。新命名規則導入後は再分析を推奨
- 次回更新: 毎週月曜 9:00 JST（自動）またはシナリオ大型施策変更後に `python scripts/update_seasonal_insights.py` を手動実行
"""


# ===== git操作 =====
def git_commit_push(today_str: str):
    def run(cmd):
        return subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True, encoding='utf-8')

    # 変更があるか確認
    diff = run(['git', 'diff', '--quiet', 'knowledge/creative_trend_insights.md'])
    if diff.returncode == 0:
        print("変更なし → git commit をスキップ")
        return

    run(['git', 'add', 'knowledge/creative_trend_insights.md'])
    msg = f"weekly update: creative_trend_insights {today_str}"
    commit = run(['git', 'commit', '-m', msg])
    if commit.returncode != 0:
        print(f"git commit 失敗: {commit.stderr}", file=sys.stderr)
        return
    print(f"git commit 完了: {msg}")

    push = run(['git', 'push'])
    if push.returncode != 0:
        print(f"git push 失敗: {push.stderr}", file=sys.stderr)
    else:
        print("git push 完了")


# ===== メイン =====
def main():
    today   = date.today()
    month   = today.month
    today_str = f"{today.year}年{month}月{today.day}日"

    print(f"=== update_seasonal_insights.py 開始 {today_str} ===")
    print(f"{month}月の季節変数を設定...")

    # データ取得（当日キャッシュ優先）
    df = load_cache()
    if df is None:
        creds  = get_credentials()
        client = bigquery.Client(project=PROJECT_ID, credentials=creds)
        df = fetch_bq_data(client)
        if df.empty:
            print("BQデータが0件 → 終了", file=sys.stderr)
            return
        save_cache(df)
    elif df.empty:
        print("キャッシュデータが0件 → 終了", file=sys.stderr)
        return

    # カラム付与
    df = enrich_df(df)

    # 分析
    cta_df   = analyze_cta_simple(df)
    ap_df    = analyze_appeal_simple(df)
    cb_df    = analyze_char_band_simple(df)
    tempo_df = analyze_tempo_simple(df)

    # 期間
    from datetime import timedelta
    period_end   = today.strftime('%Y-%m-%d')
    period_start = (today - timedelta(days=90)).strftime('%Y-%m-%d')

    # MD生成
    md_content = build_md(
        today_str=today_str, month=month,
        period_start=period_start, period_end=period_end,
        df=df,
        cta_df=cta_df, ap_df=ap_df, cb_df=cb_df, tempo_df=tempo_df
    )

    # ファイル書き込み
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"ファイル更新完了: {OUTPUT_FILE}")

    # git commit & push
    git_commit_push(today_str)

    print(f"=== 完了 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")


if __name__ == '__main__':
    main()
