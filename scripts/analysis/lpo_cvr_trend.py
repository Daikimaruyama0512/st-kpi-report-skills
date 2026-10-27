# LPO可視化 2: LP CVRトレンド（改修前後比較）
# 週次LP CVR（link_clicks → LINE登録）の時系列推移を可視化する
# LP改修日を指定すると前後の平均線を自動描画する
#
# 使い方:
#   python3 scripts/analysis/lpo_cvr_trend.py                              # CA+ST 直近26週
#   python3 scripts/analysis/lpo_cvr_trend.py --brand CA
#   python3 scripts/analysis/lpo_cvr_trend.py --brand ST --revision 2026-04-01
#   python3 scripts/analysis/lpo_cvr_trend.py --brand BOTH --weeks 52 --revision 2026-01-15
#
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow matplotlib japanize-matplotlib

import sys
import io
import argparse
import warnings
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
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
parser.add_argument("--brand",    choices=["CA", "ST", "BOTH"], default="BOTH")
parser.add_argument("--weeks",    type=int, default=26, help="表示週数")
parser.add_argument("--revision", type=str, default=None,
                    help="LP改修日 YYYY-MM-DD（前後の平均線を描画）")
args = parser.parse_args()

revision_dt = None
if args.revision:
    revision_dt = datetime.strptime(args.revision, "%Y-%m-%d")

# ── 認証 ─────────────────────────────────────────────────────
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
client = bigquery.Client(project="bigquery-jukust", credentials=creds)

# ── クエリ ────────────────────────────────────────────────────
DAYS = args.weeks * 7

SQL_CA = f"""
WITH daily AS (
  SELECT
    target_date AS date,
    SUM(link_clicks) AS link_clicks,
    SUM(purchase)    AS cv
  FROM `bigquery-jukust.CA_meta_rpt.v_CA_meta_ads_daily_report_with_scenario`
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {DAYS} DAY) AND CURRENT_DATE()
  GROUP BY target_date
)
SELECT
  DATE_TRUNC(date, WEEK(MONDAY)) AS week_start,
  SUM(link_clicks) AS link_clicks,
  SUM(cv)          AS cv
FROM daily
GROUP BY week_start
ORDER BY week_start
"""

SQL_ST = f"""
WITH daily AS (
  SELECT
    target_date                    AS date,
    SUM(link_clicks)               AS link_clicks,
    SUM(complete_registration)     AS cv
  FROM `bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report`
  WHERE target_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {DAYS} DAY) AND CURRENT_DATE()
  GROUP BY target_date
)
SELECT
  DATE_TRUNC(date, WEEK(MONDAY)) AS week_start,
  SUM(link_clicks) AS link_clicks,
  SUM(cv)          AS cv
FROM daily
GROUP BY week_start
ORDER BY week_start
"""

# ── データ取得 ────────────────────────────────────────────────
datasets = {}
if args.brand in ("CA", "BOTH"):
    df_ca = client.query(SQL_CA).to_dataframe()
    df_ca["week_start"] = pd.to_datetime(df_ca["week_start"])
    df_ca["cvr"] = df_ca["cv"] / df_ca["link_clicks"].replace(0, float("nan"))
    datasets["CA"] = df_ca
    print(f"CA: {len(df_ca)} 週分取得")

if args.brand in ("ST", "BOTH"):
    df_st = client.query(SQL_ST).to_dataframe()
    df_st["week_start"] = pd.to_datetime(df_st["week_start"])
    df_st["cvr"] = df_st["cv"] / df_st["link_clicks"].replace(0, float("nan"))
    datasets["ST"] = df_st
    print(f"ST: {len(df_st)} 週分取得")

# ── 可視化 ────────────────────────────────────────────────────
BRAND_COLOR = {"CA": "#1565C0", "ST": "#E65100"}
n = len(datasets)
fig, axes = plt.subplots(n, 1, figsize=(14, 4.5 * n), sharex=False)
if n == 1:
    axes = [axes]

for ax, (brand, df) in zip(axes, datasets.items()):
    color = BRAND_COLOR[brand]
    df_valid = df.dropna(subset=["cvr"])

    ax.plot(df_valid["week_start"], df_valid["cvr"] * 100,
            marker="o", markersize=5, linewidth=1.8, color=color, label="週次CVR")

    # 4週移動平均
    df_valid = df_valid.copy()
    df_valid["cvr_ma4"] = df_valid["cvr"].rolling(4, min_periods=2).mean()
    ax.plot(df_valid["week_start"], df_valid["cvr_ma4"] * 100,
            linewidth=2.5, linestyle="--", color=color, alpha=0.5, label="4週移動平均")

    # LP改修日ライン
    if revision_dt:
        ax.axvline(revision_dt, color="red", linestyle="--", linewidth=1.5, label="LP改修日")

        pre  = df_valid[df_valid["week_start"] <  pd.Timestamp(revision_dt)]["cvr"].mean()
        post = df_valid[df_valid["week_start"] >= pd.Timestamp(revision_dt)]["cvr"].mean()

        x_min = df_valid["week_start"].min()
        x_max = df_valid["week_start"].max()

        if not pd.isna(pre):
            ax.hlines(pre * 100, xmin=x_min, xmax=revision_dt,
                      colors="gray", linestyles=":", linewidth=1.5,
                      label=f"改修前平均 {pre*100:.2f}%")
        if not pd.isna(post):
            ax.hlines(post * 100, xmin=revision_dt, xmax=x_max,
                      colors="green", linestyles=":", linewidth=1.5,
                      label=f"改修後平均 {post*100:.2f}%")

        if not pd.isna(pre) and not pd.isna(post):
            delta = (post - pre) / pre * 100
            sign = "+" if delta >= 0 else ""
            ax.annotate(f"変化: {sign}{delta:.1f}%",
                        xy=(revision_dt, (pre + post) / 2 * 100),
                        xytext=(15, 0), textcoords="offset points",
                        fontsize=10, color="red",
                        arrowprops=dict(arrowstyle="->", color="red"))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=4))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    ax.set_ylabel("LP CVR（click→CV）%", fontsize=10)
    ax.set_title(f"{brand}  週次LP CVRトレンド（直近{args.weeks}週）", fontsize=12, color=color)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(axis="y", alpha=0.3)

fig.suptitle("LP CVRトレンド分析", fontsize=14, y=1.01)
plt.tight_layout()

out = f"{DATA_DIR}/lpo_cvr_trend.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"\n[保存] {out}")
