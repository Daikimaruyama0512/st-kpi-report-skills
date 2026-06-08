# ST Meta広告 クリエイティブ傾向分析
# 分析観点: 訴求軸 / 動画の型 / シナリオ文字数 / CTA / テンポ（動画エンゲージメント）
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow pandas

import sys
import io
import re
import json
import urllib.request
import urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

# ===== 定数 =====
TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
PROJECT_ID = "bigquery-jukust"
SHEET_ID = "18Y7A7HJWwOguajbKLS65nxPfJUcxTCDX-_TCiZvJVvs"
TARGET_GID = 1951094858

APPEAL_MAP = {
    'A': 'A:安心',
    'B': 'B:承認',
    'C': 'C:自己実現',
    'D': 'D:所属',
    'E': 'E:潜在層',
    'F': 'F:企業PUSH',
    'G': 'G:潜在_3分診断',
    'H': 'H:潜在_年収診断',
    'I': 'I:プロ講師_3分診断',
}

VIDEO_TYPE_MAP = {
    '01': '01:UGC',
    '02': '02:インタビュー',
    '03': '03:中の人',
    '04': '04:ビジネスライク',
    '05': '05:アニメ',
    '06': '06:UGC強フック',
    '07': '07:インタビューUGC風',
    '08': '08:インタビュー漫画',
}

VERIFY_MAP = {
    '00': '00:オリジナル',
    '01': '01:フック変更',
    '02': '02:CTA変更',
    '07': '07:摩耗防止',
}

# 旧命名規則: 先頭セグメントコード → 訴求セグメント名
OLD_SEGMENT_MAP = [
    (r'^01タイパ|^01_?タイパ',     'タイパ重視層（C:自己実現）'),
    (r'^02単願|^02_?単願',         '単願型（A/B:安心/承認）'),
    (r'^03併願|^03_?併願',         '併願型（E:潜在層）'),
    (r'^App|^app',                 'アプリ訴求'),
    (r'^ASC',                      'ASC（自動最適化）'),
]

# 旧命名規則: ad_nameの3番目アンダースコア区切り部分 → CTA分類
AD_NAME_CTA_MAP = [
    ('ペルソナLP',   r'ペルソナLP|ペルソナlp'),
    ('ブランド診断', r'ブランド診断'),
    ('気軽に診断',   r'気軽に診断'),
    ('3分診断',      r'3分.?診断'),
    ('16タイプ診断', r'16タイプ診断'),
    ('LP',           r'^LP$'),
]

# CTA判定（scenario本文から）優先度順
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


# ===== 認証 =====
def get_credentials():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


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
ORDER BY cpa ASC
"""
    print("BigQuery クエリ実行中...")
    df = client.query(query).to_dataframe()
    print(f"取得完了: {len(df)} 広告（spend>=1万円）")
    return df


# ===== Sheets: シナリオ補完 =====
def fetch_sheet_scenarios(token):
    def api_get(url):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode('utf-8'))

    try:
        meta = api_get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
            f"?fields=sheets.properties"
        )
        tab_name = None
        for s in meta['sheets']:
            if s['properties'].get('sheetId') == TARGET_GID:
                tab_name = s['properties']['title']
                break
        if not tab_name:
            print("警告: 対象シートタブが見つかりませんでした。シナリオ補完をスキップします。")
            return {}

        encoded = urllib.parse.quote(f"'{tab_name}'!A1:Z500")
        data = api_get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
            f"/values/{encoded}?valueRenderOption=FORMATTED_VALUE"
        )
        rows = data.get('values', [])
        if not rows:
            return {}

        # ヘッダー行を探す
        header_row_idx = None
        ad_col = scenario_col = None
        for i, row in enumerate(rows[:20]):
            for j, cell in enumerate(row):
                cell_lower = str(cell).lower().strip()
                if 'ad_name' in cell_lower or '広告名' in cell_lower:
                    header_row_idx = i
                    ad_col = j
                if 'scenario' in cell_lower or 'シナリオ' in cell_lower:
                    scenario_col = j

            if header_row_idx is not None and ad_col is not None and scenario_col is not None:
                break

        if ad_col is None or scenario_col is None:
            print("警告: スプレッドシートにad_name/scenarioカラムが見つかりませんでした。")
            return {}

        scenario_dict = {}
        for row in rows[header_row_idx + 1:]:
            if len(row) > max(ad_col, scenario_col):
                name = str(row[ad_col]).strip()
                scen = str(row[scenario_col]).strip()
                if name and scen:
                    scenario_dict[name] = scen

        print(f"スプレッドシートからシナリオ {len(scenario_dict)} 件取得")
        return scenario_dict

    except Exception as e:
        print(f"警告: スプレッドシート読み取りエラー ({e})。シナリオ補完をスキップします。")
        return {}


def fill_scenarios(df, sheet_dict):
    def resolve(row):
        s = row['scenario']
        if s and str(s).strip():
            return str(s).strip()
        # スプレッドシートで補完
        return sheet_dict.get(row['ad_name'], '')

    df['scenario_filled'] = df.apply(resolve, axis=1)
    null_count = (df['scenario_filled'] == '').sum()
    print(f"シナリオあり: {len(df) - null_count} 件 / なし: {null_count} 件")
    return df


# ===== 命名規則パース =====
NAMING_RE = re.compile(r'^([NE])([VPM])_([A-I])(\d{2})(\d{2})(\d)_(\d{6})')

def parse_old_segment(ad_name):
    """旧命名規則から訴求セグメントを抽出"""
    for pattern, label in OLD_SEGMENT_MAP:
        if re.search(pattern, str(ad_name)):
            return label
    return '不明（旧命名）'

def parse_ad_name_cta(ad_name):
    """旧命名規則のad_nameからCTAを抽出（アンダースコア区切り3番目）"""
    parts = str(ad_name).split('_')
    # 2番目以降でCTAキーワードを探す（"01タイパ"/"02単願" は1番目なのでスキップ）
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
            'is_new': True,
            'appeal': APPEAL_MAP.get(m.group(3), m.group(3) + ':不明'),
            'video_type': VIDEO_TYPE_MAP.get(m.group(4), m.group(4) + ':不明'),
            'verify': VERIFY_MAP.get(m.group(5), m.group(5) + ':不明'),
            'cta_from_name': None,
        }
    # 旧命名規則として解析
    return {
        'is_new': False,
        'appeal': parse_old_segment(ad_name),
        'video_type': 'UGC系（推定）',  # ST広告は主にUGC動画
        'verify': '不明（旧命名）',
        'cta_from_name': parse_ad_name_cta(ad_name),
    }

def add_parsed_columns(df):
    parsed = df['ad_name'].apply(parse_ad_name)
    df['appeal'] = parsed.apply(lambda x: x['appeal'])
    df['video_type'] = parsed.apply(lambda x: x['video_type'])
    df['verify'] = parsed.apply(lambda x: x['verify'])
    df['cta_from_name'] = parsed.apply(lambda x: x['cta_from_name'])
    df['is_new_naming'] = parsed.apply(lambda x: x['is_new'])
    old_count = (~df['is_new_naming']).sum()
    new_count = df['is_new_naming'].sum()
    if old_count > 0:
        print(f"旧命名規則: {old_count} 件（セグメントから訴求軸を推定）")
    if new_count > 0:
        print(f"新命名規則: {new_count} 件")
    return df


# ===== CTA抽出 =====
def extract_cta_from_scenario(text):
    if not text or not str(text).strip():
        return None
    for label, pattern in CTA_PATTERNS:
        if re.search(pattern, str(text)):
            return label
    return 'その他'

def extract_cta(row):
    """ad_nameのCTA → scenarioのCTA の順で優先。両方なければ'(シナリオなし)'"""
    # ad_nameから取得済みCTAを優先
    if row.get('cta_from_name'):
        return row['cta_from_name']
    # scenarioテキストから判定
    result = extract_cta_from_scenario(row.get('scenario_filled', ''))
    if result:
        return result
    return '(シナリオなし)'

def add_cta_column(df):
    df['cta_type'] = df.apply(extract_cta, axis=1)
    return df


# ===== 文字数帯 =====
def char_band(n):
    if n == 0:
        return '0:シナリオなし'
    if n <= 200:
        return '1:1-200字'
    if n <= 400:
        return '2:201-400字'
    return '3:401字以上'

def add_char_band(df):
    df['scenario_len'] = df['scenario_filled'].apply(lambda x: len(str(x)) if x else 0)
    df['char_band'] = df['scenario_len'].apply(char_band)
    return df


# ===== 各分析 =====

def agg_group(df, group_col, extra_aggs=None):
    aggs = {
        'spend': ('spend', 'sum'),
        'cv': ('cv', 'sum'),
        'link_clicks': ('link_clicks', 'sum'),
        'ad_count': ('ad_name', 'count'),
    }
    if extra_aggs:
        aggs.update(extra_aggs)
    result = df.groupby(group_col).agg(**aggs).reset_index()
    result['cpa'] = result['spend'] / result['cv'].replace(0, float('nan'))
    result['cvr_pct'] = result['cv'] / result['link_clicks'].replace(0, float('nan')) * 100
    return result.sort_values('cpa')


def analyze_appeal(df):
    return agg_group(df, 'appeal')


def analyze_video_type(df):
    """動画の型が旧命名では不明なため、訴求セグメント別に視聴完了率+CPAで分析"""
    result = df.groupby('appeal').agg(
        spend=('spend', 'sum'),
        cv=('cv', 'sum'),
        link_clicks=('link_clicks', 'sum'),
        impressions=('impressions', 'sum'),
        video_p100=('video_p100', 'sum'),
        ad_count=('ad_name', 'count'),
    ).reset_index()
    result['cpa'] = result['spend'] / result['cv'].replace(0, float('nan'))
    result['cvr_pct'] = result['cv'] / result['link_clicks'].replace(0, float('nan')) * 100
    result['completion_rate_pct'] = result['video_p100'] / result['impressions'].replace(0, float('nan')) * 100
    result = result.rename(columns={'appeal': 'segment'})
    return result.sort_values('cpa')


def analyze_char_band(df):
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


def analyze_cta(df):
    return agg_group(df, 'cta_type')


def analyze_tempo(df):
    # 動画広告のみ（3秒再生数>0）
    vdf = df[df['video_view_3s'] > 0].copy()
    if vdf.empty:
        print("テンポ分析: 動画広告データなし")
        return pd.DataFrame()

    total_imp = vdf['impressions'].sum()
    avg = {
        '3s':  vdf['video_view_3s'].sum() / total_imp,
        'p25': vdf['video_p25'].sum()     / total_imp,
        'p50': vdf['video_p50'].sum()     / total_imp,
        'p75': vdf['video_p75'].sum()     / total_imp,
        'p100':vdf['video_p100'].sum()    / total_imp,
    }

    vdf['tempo_good'] = (
        (vdf['rate_3s']   >= avg['3s'])  &
        (vdf['rate_p25']  >= avg['p25']) &
        (vdf['rate_p50']  >= avg['p50']) &
        (vdf['rate_p75']  >= avg['p75']) &
        (vdf['rate_p100'] >= avg['p100'])
    )
    vdf['tempo_label'] = vdf['tempo_good'].map({True: 'テンポ良好群', False: 'テンポ不良群'})

    result = vdf.groupby('tempo_label').agg(
        spend=('spend', 'sum'),
        cv=('cv', 'sum'),
        link_clicks=('link_clicks', 'sum'),
        ad_count=('ad_name', 'count'),
        avg_rate_3s=('rate_3s', 'mean'),
        avg_rate_p25=('rate_p25', 'mean'),
        avg_rate_p50=('rate_p50', 'mean'),
        avg_rate_p75=('rate_p75', 'mean'),
        avg_rate_p100=('rate_p100', 'mean'),
    ).reset_index()
    result['cpa'] = result['spend'] / result['cv'].replace(0, float('nan'))
    result['cvr_pct'] = result['cv'] / result['link_clicks'].replace(0, float('nan')) * 100
    return result.sort_values('cpa')


# ===== 出力ヘルパー =====

def fmt_yen(v):
    if v != v:  # NaN
        return '-'
    return f"{int(v):,}"

def fmt_pct(v, digits=1):
    if v != v:
        return '-'
    return f"{v:.{digits}f}%"

def fmt_num(v, digits=0):
    if v != v:
        return '-'
    if digits == 0:
        return f"{int(v):,}"
    return f"{v:.{digits}f}"


def print_section(title, conclusion, table_str, actions):
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"[{title}]")
    print(sep)
    print("\n【結論】")
    print(f"  {conclusion}")
    print("\n【根拠データ】")
    print(table_str)
    print("\n【推奨アクション】")
    for i, a in enumerate(actions, 1):
        print(f"  {i}. {a}")


# ===== 結論・アクション生成 =====

def summarize_appeal(df):
    if df.empty:
        return "データなし", []
    valid = df[df['cv'] > 0].copy()
    if valid.empty:
        return "CV獲得済みデータなし", []
    best = valid.sort_values('cpa').iloc[0]
    worst = valid.sort_values('cpa').iloc[-1] if len(valid) > 1 else None

    conclusion = f"訴求軸「{best['appeal']}」がCPA最良（{fmt_yen(best['cpa'])}円）、CVR {fmt_pct(best['cvr_pct'])}。"
    if worst is not None and worst['appeal'] != best['appeal']:
        conclusion += f"「{worst['appeal']}」はCPA高止まり（{fmt_yen(worst['cpa'])}円）。"

    actions = [
        f"「{best['appeal']}」向けシナリオを量産し、予算を重点配分する",
    ]
    if worst is not None and worst['spend'] > 100000:
        actions.append(f"「{worst['appeal']}」はシナリオ内のインサイト刺さり方を再点検し、フック改善を優先する")
    actions.append("旧命名広告はシナリオ確認後、新命名規則（訴求軸A-I/動画型）に移行して管理精度を高める")
    return conclusion, actions[:3]


def summarize_video_type(df):
    if df.empty:
        return "データなし", []
    valid = df[df['cv'] > 0]
    if valid.empty:
        return "CV獲得済みデータなし", []
    best = valid.sort_values('cpa').iloc[0]
    worst = valid.sort_values('cpa').iloc[-1] if len(valid) > 1 else None
    conclusion = (
        f"セグメント「{best['segment']}」がCPA最良（{fmt_yen(best['cpa'])}円）、"
        f"CVR {fmt_pct(best['cvr_pct'])}、動画完了率 {fmt_pct(best['completion_rate_pct'])}。"
    )
    if worst is not None and worst['segment'] != best['segment']:
        conclusion += f"「{worst['segment']}」はCPA {fmt_yen(worst['cpa'])}円で最も高コスト。"
    actions = [
        f"セグメント「{best['segment']}」へ予算を重点配分し、類似シナリオの量産を優先する",
        "動画完了率が低いセグメントはシナリオ冒頭フックと中盤の構成を見直す",
        "全セグメントで旧命名から新命名規則への移行を進め、訴求軸の可視化と管理精度を高める",
    ]
    return conclusion, actions[:3]


def summarize_char_band(df):
    if df.empty:
        return "データなし", []
    valid = df[df['cv'] > 0].copy()
    if valid.empty:
        return "CV獲得済みデータなし", []
    best = valid.sort_values('cpa').iloc[0]
    conclusion = (
        f"文字数帯「{best['char_band']}」がCPA最良（{fmt_yen(best['cpa'])}円）、"
        f"平均 {fmt_num(best['avg_len'], 0)} 字。"
    )
    actions = [
        f"シナリオ文字数の目安を「{best['char_band']}」に合わせて設計する",
        "シナリオなし（NULL/空）の広告はシナリオを付与し、統制条件を揃えてから再評価する",
        "文字数が多い広告は主要メッセージに絞り込み、視聴者の離脱を防ぐ構成を検討する",
    ]
    return conclusion, actions


def summarize_cta(df):
    if df.empty:
        return "データなし", []
    valid = df[df['cv'] > 0].copy()
    if valid.empty:
        return "CV獲得済みデータなし", []
    best = valid.sort_values('cpa').iloc[0]
    conclusion = (
        f"CTA「{best['cta_type']}」がCPA最良（{fmt_yen(best['cpa'])}円）、"
        f"CVR {fmt_pct(best['cvr_pct'])}。"
    )
    actions = [
        f"CTA「{best['cta_type']}」を基軸にシナリオを設計する",
        "CTA変更バリアント（命名規則:02）でA/Bテストを実施し、効果を定量検証する",
        "CTAと遷移先LPの期待値を一致させ（Meta→LP→LINE統一）、CVR低下を防ぐ",
    ]
    return conclusion, actions


def summarize_tempo(df):
    if df.empty:
        return "データなし", []
    good = df[df['tempo_label'] == 'テンポ良好群']
    bad  = df[df['tempo_label'] == 'テンポ不良群']
    if good.empty:
        return "テンポ良好群の広告なし", []
    g = good.iloc[0]
    conclusion = (
        f"テンポ良好群はCPA {fmt_yen(g['cpa'])}円、"
    )
    if not bad.empty:
        b = bad.iloc[0]
        conclusion += f"テンポ不良群（{fmt_yen(b['cpa'])}円）比で差がある。"
    conclusion += "3秒再生率・完了率ともに高い広告が成果を牽引。"
    actions = [
        "3秒再生率が低い広告はフック（冒頭0.5秒）を優先的に差し替える",
        "p50→p75で離脱が急増する広告はシナリオ中盤の構成を再検討する（PASONA中段のA→S部分）",
        "テンポ良好群の動画構成（カット割り・尺・BGM）を社内ナレッジ化して横展開する",
    ]
    return conclusion, actions


# ===== テーブル表示 =====

def df_to_str(df, cols, headers, widths):
    lines = []
    header = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    sep    = "-+-".join("-" * w for w in widths)
    lines.append("  " + header)
    lines.append("  " + sep)
    for _, row in df.iterrows():
        cells = []
        for col, w in zip(cols, widths):
            v = row[col]
            cells.append(str(v)[:w].ljust(w))
        lines.append("  " + " | ".join(cells))
    return "\n".join(lines)


# ===== CSV保存 =====

def save_csv(results_map, out_path):
    frames = []
    for section, df in results_map.items():
        if df is not None and not df.empty:
            tmp = df.copy()
            tmp.insert(0, 'section', section)
            frames.append(tmp)
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"\nCSV保存完了: {out_path}")


# ===== メイン =====

def main():
    print("ST Meta広告 クリエイティブ傾向分析を開始します")
    print("=" * 60)

    # 認証
    creds = get_credentials()
    bq_client = bigquery.Client(project=PROJECT_ID, credentials=creds)

    # BigQueryデータ取得
    df = fetch_bq_data(bq_client)
    if df.empty:
        print("分析対象データがありませんでした。")
        return

    # シナリオ補完（Sheets API）
    sheet_dict = fetch_sheet_scenarios(creds.token)
    df = fill_scenarios(df, sheet_dict)

    # パース列追加
    df = add_parsed_columns(df)
    df = add_cta_column(df)
    df = add_char_band(df)

    # 各分析実行
    appeal_df    = analyze_appeal(df)
    video_df     = analyze_video_type(df)
    char_df      = analyze_char_band(df)
    cta_df       = analyze_cta(df)
    tempo_df     = analyze_tempo(df)

    # ===== 出力: 訴求軸 =====
    appeal_display = appeal_df.copy()
    appeal_display['spend_fmt'] = appeal_display['spend'].apply(fmt_yen)
    appeal_display['cv_fmt']    = appeal_display['cv'].apply(lambda x: fmt_num(x))
    appeal_display['cpa_fmt']   = appeal_display['cpa'].apply(fmt_yen)
    appeal_display['cvr_fmt']   = appeal_display['cvr_pct'].apply(fmt_pct)

    tbl = df_to_str(
        appeal_display,
        cols    =['appeal',   'spend_fmt', 'cv_fmt', 'cpa_fmt', 'cvr_fmt', 'ad_count'],
        headers =['訴求軸',   'spend(円)', 'CV数',   'CPA(円)', 'CVR',     '広告数'],
        widths  =[18, 14, 6, 10, 7, 5],
    )
    conc, acts = summarize_appeal(appeal_df)
    print_section("1. 訴求軸別成果", conc, tbl, acts)

    # ===== 出力: 訴求セグメント別（動画完了率付き） =====
    video_display = video_df.copy()
    video_display['spend_fmt']   = video_display['spend'].apply(fmt_yen)
    video_display['cv_fmt']      = video_display['cv'].apply(fmt_num)
    video_display['cpa_fmt']     = video_display['cpa'].apply(fmt_yen)
    video_display['cvr_fmt']     = video_display['cvr_pct'].apply(fmt_pct)
    video_display['comp_fmt']    = video_display['completion_rate_pct'].apply(fmt_pct)

    tbl2 = df_to_str(
        video_display,
        cols    =['segment',        'spend_fmt', 'cv_fmt', 'cpa_fmt', 'cvr_fmt', 'comp_fmt', 'ad_count'],
        headers =['訴求セグメント', 'spend(円)', 'CV数',   'CPA(円)', 'CVR',     '動画完了率', '広告数'],
        widths  =[22, 14, 6, 10, 7, 10, 5],
    )
    conc2, acts2 = summarize_video_type(video_df)
    print_section("2. 訴求セグメント別成果（動画完了率付き）", conc2, tbl2, acts2)

    # ===== 出力: 文字数 =====
    char_display = char_df.copy()
    char_display['spend_fmt'] = char_display['spend'].apply(fmt_yen)
    char_display['cv_fmt']    = char_display['cv'].apply(fmt_num)
    char_display['cpa_fmt']   = char_display['cpa'].apply(fmt_yen)
    char_display['cvr_fmt']   = char_display['cvr_pct'].apply(fmt_pct)
    char_display['avg_len_fmt'] = char_display['avg_len'].apply(lambda x: fmt_num(x, 0) + '字')

    tbl3 = df_to_str(
        char_display,
        cols    =['char_band',   'avg_len_fmt', 'spend_fmt', 'cv_fmt', 'cpa_fmt', 'cvr_fmt', 'ad_count'],
        headers =['文字数帯',    '平均文字数',  'spend(円)', 'CV数',   'CPA(円)', 'CVR',     '広告数'],
        widths  =[16, 10, 14, 6, 10, 7, 5],
    )
    conc3, acts3 = summarize_char_band(char_df)
    print_section("3. シナリオ文字数別成果", conc3, tbl3, acts3)

    # ===== 出力: CTA =====
    cta_display = cta_df.copy()
    cta_display['spend_fmt'] = cta_display['spend'].apply(fmt_yen)
    cta_display['cv_fmt']    = cta_display['cv'].apply(fmt_num)
    cta_display['cpa_fmt']   = cta_display['cpa'].apply(fmt_yen)
    cta_display['cvr_fmt']   = cta_display['cvr_pct'].apply(fmt_pct)

    tbl4 = df_to_str(
        cta_display,
        cols    =['cta_type', 'spend_fmt', 'cv_fmt', 'cpa_fmt', 'cvr_fmt', 'ad_count'],
        headers =['CTA種別',  'spend(円)', 'CV数',   'CPA(円)', 'CVR',     '広告数'],
        widths  =[14, 14, 6, 10, 7, 5],
    )
    conc4, acts4 = summarize_cta(cta_df)
    print_section("4. CTA別成果", conc4, tbl4, acts4)

    # ===== 出力: テンポ =====
    if not tempo_df.empty:
        tempo_display = tempo_df.copy()
        tempo_display['spend_fmt']    = tempo_display['spend'].apply(fmt_yen)
        tempo_display['cv_fmt']       = tempo_display['cv'].apply(fmt_num)
        tempo_display['cpa_fmt']      = tempo_display['cpa'].apply(fmt_yen)
        tempo_display['cvr_fmt']      = tempo_display['cvr_pct'].apply(fmt_pct)
        tempo_display['rate_3s_fmt']  = (tempo_display['avg_rate_3s'] * 100).apply(fmt_pct)
        tempo_display['rate_100_fmt'] = (tempo_display['avg_rate_p100'] * 100).apply(fmt_pct)

        tbl5 = df_to_str(
            tempo_display,
            cols    =['tempo_label',   'spend_fmt', 'cv_fmt', 'cpa_fmt', 'rate_3s_fmt', 'rate_100_fmt', 'ad_count'],
            headers =['テンポ区分',    'spend(円)', 'CV数',   'CPA(円)', '3秒再生率',   '完了率',       '広告数'],
            widths  =[16, 14, 6, 10, 10, 8, 5],
        )
        conc5, acts5 = summarize_tempo(tempo_df)
        print_section("5. テンポ（動画エンゲージメント）別成果", conc5, tbl5, acts5)

    # CSV保存
    out_path = "/Users/119322/claude-code-template_af/scripts/analysis_result.csv"
    save_csv({
        'appeal':    appeal_df,
        'video_type': video_df,
        'char_band': char_df,
        'cta':       cta_df,
        'tempo':     tempo_df if not tempo_df.empty else None,
    }, out_path)

    print("\n分析完了。")


if __name__ == "__main__":
    main()
