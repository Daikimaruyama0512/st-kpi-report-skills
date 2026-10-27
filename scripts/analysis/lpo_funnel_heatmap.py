# LPO可視化 1: ファネル離脱ヒートマップ
# 広告インプレッション → クリック → LINE登録 の各ステップ転換率を可視化する
#
# 使い方:
#   python3 scripts/analysis/lpo_funnel_heatmap.py            # CA+ST 直近90日
#   python3 scripts/analysis/lpo_funnel_heatmap.py --brand CA
#   python3 scripts/analysis/lpo_funnel_heatmap.py --brand ST
#   python3 scripts/analysis/lpo_funnel_heatmap.py --days 30
#
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow matplotlib japanize-matplotlib

import sys
import io
import argparse
import warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from google.oauth2.credentials import Credentials
from google.cloud import bigquery

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
warnings.filterwarnings("ignore")

BASE_DIR   = "/Users/119322/Desktop/claude-code-template_af"
TOKEN_FILE = f"{BASE_DIR}/secrets/token.json"
DATA_DIR   = f"{BASE_DIR}/scripts/data"
SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
]

try:
    import japanize_matplotlib
    japanize_matplotlib.japanize()
    JP = True
except ImportError:
    JP = False

# ── 引数 ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--brand", choices=["CA", "ST", "BOTH"], default="BOTH")
parser.add_argument("--days",  type=int, default=90, help="集計期間（日）")
args = parser.parse_args()

# ── 認証 ─────────────────────────────────────────────────────
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
client = bigquery.Client(project="bigquery-jukust", credentials=creds)

# ── クエリ ────────────────────────────────────────────────────
SQL_CA = f"""
WITH agg AS (
  SELECT
    SUM(impressions)  AS impressions,
    SUM(link_clicks)  AS link_clicks,
    SUM(purchase)     AS cv
  FROM `bigquery-jukust.CA_meta_rpt.v_CA_meta_ads_daily_report_with_scenario`
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {args.days} DAY) AND CURRENT_DATE()
)
SELECT 'CA' AS brand, impressions, link_clicks, cv FROM agg
"""

SQL_ST = f"""
WITH agg AS (
  SELECT
    SUM(impressions)           AS impressions,
    SUM(link_clicks)           AS link_clicks,
    SUM(complete_registration) AS cv
  FROM `bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report`
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {args.days} DAY) AND CURRENT_DATE()
)
SELECT 'ST' AS brand, impressions, link_clicks, cv FROM agg
"""

# ── データ取得 ────────────────────────────────────────────────
targets = []
if args.brand in ("CA", "BOTH"):
    row = list(client.query(SQL_CA).result())[0]
    targets.append({"brand": "CA", "impressions": row.impressions,
                    "link_clicks": row.link_clicks, "cv": int(row.cv or 0)})
    print(f"CA: IMP={row.impressions:,}  CLK={row.link_clicks:,}  CV={int(row.cv or 0):,}")

if args.brand in ("ST", "BOTH"):
    row = list(client.query(SQL_ST).result())[0]
    targets.append({"brand": "ST", "impressions": row.impressions,
                    "link_clicks": row.link_clicks, "cv": int(row.cv or 0)})
    print(f"ST: IMP={row.impressions:,}  CLK={row.link_clicks:,}  CV={int(row.cv or 0):,}")

# ── 可視化 ────────────────────────────────────────────────────
BRAND_COLOR = {"CA": "#1565C0", "ST": "#E65100"}
STEP_LABELS = ["インプレッション", "広告クリック\n（LP到達）", "LINE登録\n（FV CV）"]

n_brands = len(targets)
fig, axes = plt.subplots(1, n_brands, figsize=(6 * n_brands, 6))
if n_brands == 1:
    axes = [axes]

for ax, data in zip(axes, targets):
    brand = data["brand"]
    values = [data["impressions"], data["link_clicks"], data["cv"]]

    # 転換率（初回比・ステップ比）
    rates_from_top  = [v / values[0] * 100 for v in values]
    rates_step = [100.0]
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            rates_step.append(values[i] / values[i - 1] * 100)
        else:
            rates_step.append(0.0)

    # 棒の色: CVRが低いほど赤
    bar_colors = []
    for r in rates_from_top:
        if r >= 5:
            bar_colors.append("#2e7d32")   # 緑
        elif r >= 1:
            bar_colors.append("#f9a825")   # 黄
        else:
            bar_colors.append("#c62828")   # 赤

    y_pos = np.arange(len(STEP_LABELS))
    bars = ax.barh(y_pos, rates_from_top, color=bar_colors, height=0.5, edgecolor="white")

    # ラベル: 件数 + 転換率
    for i, (bar, val, r_top, r_step) in enumerate(zip(bars, values, rates_from_top, rates_step)):
        step_txt = f"  ステップ転換: {r_step:.1f}%" if i > 0 else ""
        ax.text(bar.get_width() + 0.3,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}件  ({r_top:.2f}%){step_txt}",
                va="center", fontsize=9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(STEP_LABELS, fontsize=10)
    ax.set_xlabel("初回流入（インプレッション）比率 (%)", fontsize=9)
    ax.set_title(f"{brand}  ファネル離脱ヒートマップ\n直近{args.days}日", fontsize=12,
                 color=BRAND_COLOR[brand])
    ax.set_xlim(0, max(rates_from_top) * 1.5)
    ax.invert_yaxis()

    # 凡例
    patches = [
        mpatches.Patch(color="#2e7d32", label="転換率 5%以上"),
        mpatches.Patch(color="#f9a825", label="転換率 1–5%"),
        mpatches.Patch(color="#c62828", label="転換率 1%未満"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=8)

fig.suptitle(f"LPO ファネル離脱ヒートマップ（直近{args.days}日）", fontsize=14, y=1.02)
plt.tight_layout()

out = f"{DATA_DIR}/lpo_funnel_heatmap.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"\n[保存] {out}")
