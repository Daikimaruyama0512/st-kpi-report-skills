# LPO可視化 3: A/Bテスト 信頼区間チャート
# 2つの期間（または2つのキャンペーン）のLP CVRを統計的に比較する
#
# 使い方（期間比較）:
#   python3 scripts/analysis/lpo_ab_test.py \
#       --brand CA \
#       --period-a 2026-01-01 2026-03-31 \
#       --period-b 2026-04-01 2026-06-30 \
#       --label-a "改修前LP" --label-b "改修後LP"
#
# 使い方（キャンペーン比較）:
#   python3 scripts/analysis/lpo_ab_test.py \
#       --brand ST \
#       --campaign-a "キャンペーン名A" \
#       --campaign-b "キャンペーン名B"
#
# デフォルト: CA+ST 直近90日を前半45日 vs 後半45日で比較
#
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow matplotlib scipy japanize-matplotlib

import sys
import io
import argparse
import warnings
from datetime import datetime, date, timedelta
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
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
except ImportError:
    pass

# ── 引数 ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--brand", choices=["CA", "ST", "BOTH"], default="BOTH")
parser.add_argument("--period-a", nargs=2, metavar=("START", "END"), default=None,
                    help="期間A（YYYY-MM-DD YYYY-MM-DD）")
parser.add_argument("--period-b", nargs=2, metavar=("START", "END"), default=None,
                    help="期間B（YYYY-MM-DD YYYY-MM-DD）")
parser.add_argument("--label-a",    type=str, default="期間A（前）")
parser.add_argument("--label-b",    type=str, default="期間B（後）")
parser.add_argument("--campaign-a", type=str, default=None, help="比較キャンペーン名A（部分一致）")
parser.add_argument("--campaign-b", type=str, default=None, help="比較キャンペーン名B（部分一致）")
args = parser.parse_args()

# デフォルト期間: 直近90日を前後45日に分割
today = date.today()
if args.period_a is None:
    end_a   = today - timedelta(days=46)
    start_a = today - timedelta(days=90)
    args.period_a = [start_a.isoformat(), end_a.isoformat()]
    args.label_a  = f"前半45日\n({start_a} ~ {end_a})"

if args.period_b is None:
    end_b   = today
    start_b = today - timedelta(days=45)
    args.period_b = [start_b.isoformat(), end_b.isoformat()]
    args.label_b  = f"後半45日\n({start_b} ~ {end_b})"

# ── 認証 ─────────────────────────────────────────────────────
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
client = bigquery.Client(project="bigquery-jukust", credentials=creds)

# ── クエリ構築 ────────────────────────────────────────────────
def build_query(brand, start, end, campaign_filter=None):
    if brand == "CA":
        table = "bigquery-jukust.CA_meta_rpt.v_CA_meta_ads_daily_report_with_scenario"
        date_col = "target_date"
        cv_col   = "purchase"
        camp_col = "campaign_name"
    else:  # ST
        table    = "bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report"
        date_col = "target_date"
        cv_col   = "complete_registration"
        camp_col = "campaign_name"

    camp_clause = ""
    if campaign_filter:
        escaped = campaign_filter.replace("'", "\\'")
        camp_clause = f"AND {camp_col} LIKE '%{escaped}%'"

    return f"""
WITH agg AS (
  SELECT
    SUM(link_clicks) AS link_clicks,
    SUM({cv_col})    AS cv
  FROM `{table}`
  WHERE {date_col} BETWEEN '{start}' AND '{end}'
  {camp_clause}
)
SELECT link_clicks, CAST(cv AS INT64) AS cv FROM agg
"""

# ── 信頼区間計算 ──────────────────────────────────────────────
def calc_ci(cv, n, z=1.96):
    """二項分布の95%信頼区間（Wald法）"""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = cv / n
    margin = z * np.sqrt(p * (1 - p) / n)
    return p, max(0, p - margin), min(1, p + margin)

# ── データ取得・検定 ──────────────────────────────────────────
BRAND_COLOR = {"CA": "#1565C0", "ST": "#E65100"}
brands = ["CA", "ST"] if args.brand == "BOTH" else [args.brand]

fig, axes = plt.subplots(1, len(brands), figsize=(6 * len(brands), 5))
if len(brands) == 1:
    axes = [axes]

for ax, brand in zip(axes, brands):
    camp_a = args.campaign_a
    camp_b = args.campaign_b

    row_a = list(client.query(build_query(brand, *args.period_a, camp_a)).result())[0]
    row_b = list(client.query(build_query(brand, *args.period_b, camp_b)).result())[0]

    n_a, cv_a = int(row_a.link_clicks or 0), int(row_a.cv or 0)
    n_b, cv_b = int(row_b.link_clicks or 0), int(row_b.cv or 0)

    print(f"{brand} 期間A: clicks={n_a:,}  cv={cv_a:,}")
    print(f"{brand} 期間B: clicks={n_b:,}  cv={cv_b:,}")

    # CVR + 信頼区間
    cvr_a, ci_a_lo, ci_a_hi = calc_ci(cv_a, n_a)
    cvr_b, ci_b_lo, ci_b_hi = calc_ci(cv_b, n_b)

    # カイ二乗検定
    if n_a > 0 and n_b > 0 and cv_a > 0 and cv_b > 0:
        _, p_val, _, _ = stats.chi2_contingency([
            [cv_a, n_a - cv_a],
            [cv_b, n_b - cv_b],
        ])
    else:
        p_val = 1.0

    sig_label = "p < 0.05 ✓有意差あり" if p_val < 0.05 else f"p={p_val:.3f} 有意差なし"
    bar_color_a = BRAND_COLOR[brand]
    bar_color_b = "#2e7d32" if cvr_b >= cvr_a else "#c62828"

    x = [0, 1]
    cvrs = [cvr_a * 100, cvr_b * 100]
    yerr_lo = [
        (cvr_a - ci_a_lo) * 100,
        (cvr_b - ci_b_lo) * 100,
    ]
    yerr_hi = [
        (ci_a_hi - cvr_a) * 100,
        (ci_b_hi - cvr_b) * 100,
    ]

    bars = ax.bar(x, cvrs,
                  color=[bar_color_a, bar_color_b],
                  width=0.45, alpha=0.85, edgecolor="white", linewidth=1.2)
    ax.errorbar(x, cvrs,
                yerr=[yerr_lo, yerr_hi],
                fmt="none", color="black", capsize=8, linewidth=1.5)

    # 数値ラベル
    for xi, (bar, cvr, cv, n) in enumerate(zip(bars, cvrs, [cv_a, cv_b], [n_a, n_b])):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + yerr_hi[xi] + 0.05,
                f"{cvr:.2f}%\n({cv:,}/{n:,}件)",
                ha="center", va="bottom", fontsize=9)

    # リフト表示
    if cvr_a > 0:
        lift = (cvr_b - cvr_a) / cvr_a * 100
        sign = "+" if lift >= 0 else ""
        lift_color = "#2e7d32" if lift >= 0 else "#c62828"
        ax.annotate(f"リフト: {sign}{lift:.1f}%",
                    xy=(0.5, max(cvrs) * 0.5),
                    ha="center", fontsize=12, color=lift_color, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([args.label_a, args.label_b], fontsize=10)
    ax.set_ylabel("LP CVR（click→CV）%", fontsize=10)
    ax.set_title(f"{brand}  A/Bテスト 信頼区間チャート\n{sig_label}",
                 fontsize=11, color=BRAND_COLOR[brand])
    ax.set_ylim(0, max(cvrs) * 1.6 + 0.1)
    ax.grid(axis="y", alpha=0.3)

    # 凡例（エラーバー説明）
    ax.text(0.98, 0.02, "エラーバー = 95%信頼区間（Wald法）\n棒が重なれば有意差なし",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="gray",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))

fig.suptitle("LP A/Bテスト 統計的有意差検定", fontsize=14, y=1.01)
plt.tight_layout()

out = f"{DATA_DIR}/lpo_ab_test.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"\n[保存] {out}")
