# TOP10広告のシナリオをBigQueryから取得
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import bigquery

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = ['https://www.googleapis.com/auth/bigquery', 'https://www.googleapis.com/auth/drive']
PROJECT_ID = "bigquery-jukust"

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

client = bigquery.Client(project=PROJECT_ID, credentials=creds)

# TOP10広告名（完全一致を試みる）
target_ads = [
    "02単願_塾バイト探しキャンセル界隈_ブランド診断_新規",
    "02単願_失敗したくないなら診断_気軽に診断_横展開",
    "01タイパ_効率よく探せる_ブランド診断",
    "02単願_性格に合う_ブランド診断",
    "01タイパ_受験経験をお金に_ブランド診断_新規",
    "02単願_経験を資産に_ブランド診断_横展開",
    "01タイパ_指導に集中_ブランド診断",
    "ASC_動画_UGC113",
    "02単願_性格に合う_16タイプ診断",
    "01タイパ_教えることで理解が深まる_ブランド診断_新規",
]

# 完全一致クエリ
print("=== 完全一致 ===")
placeholders = ', '.join([f"'{a}'" for a in target_ads])
q = f"""
SELECT ad_name, scenario
FROM `bigquery-jukust.ST_meta_raw.ST_meta_scenario_sync`
WHERE ad_name IN ({placeholders})
ORDER BY ad_name
"""
rows = list(client.query(q).result())
found_exact = {row.ad_name: row.scenario for row in rows}
print(f"完全一致: {len(found_exact)}件")
for name, scenario in found_exact.items():
    print(f"\n【{name}】")
    print(scenario[:200] + "..." if len(scenario) > 200 else scenario)

# 見つからなかった広告名を部分一致で検索
not_found = [a for a in target_ads if a not in found_exact]
print(f"\n=== 完全一致なし: {len(not_found)}件 → 部分一致で探す ===")
for ad in not_found:
    # 広告名の中核部分で検索
    core = ad.replace("_新規", "").replace("_横展開", "").replace("_新規V2", "")
    q2 = f"""
    SELECT ad_name, scenario
    FROM `bigquery-jukust.ST_meta_raw.ST_meta_scenario_sync`
    WHERE LOWER(ad_name) LIKE LOWER('%{core}%')
    LIMIT 3
    """
    try:
        rows2 = list(client.query(q2).result())
        print(f"\n元の広告名: 「{ad}」")
        if rows2:
            for r in rows2:
                print(f"  → 部分一致: 「{r.ad_name}」")
                print(f"     シナリオ先頭: {r.scenario[:150]}...")
        else:
            print("  → 部分一致なし")
    except Exception as e:
        print(f"  ERROR: {e}")

# --- 全広告のシナリオをまとめて出力（UTF-8 CSV保存） ---
print("\n=== 全件シナリオ取得（CSV保存）===")
q_all = """
SELECT ad_name, scenario
FROM `bigquery-jukust.ST_meta_raw.ST_meta_scenario_sync`
ORDER BY ad_name
"""
all_rows = list(client.query(q_all).result())

import csv
out_path = "/Users/119322/claude-code-template_af/scripts/st_scenarios_all.csv"
with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["ad_name", "scenario"])
    for row in all_rows:
        writer.writerow([row.ad_name, row.scenario])
print(f"CSV保存: {out_path} ({len(all_rows)}件)")
