# 広告費 vs CVR/CPA 回帰分析（訴求軸別）
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow scipy matplotlib japanize-matplotlib

import sys
import io
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from google.oauth2.credentials import Credentials
from google.cloud import bigquery

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
warnings.filterwarnings("ignore")

# ── 認証 ────────────────────────────────────────────────
TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
client = bigquery.Client(project="bigquery-jukust", credentials=creds)

# ── 訴求軸マスタ ─────────────────────────────────────────
AXIS_LABELS = {
    "A": "A: 安心",
    "B": "B: 承認",
    "C": "C: 自己実現",
    "D": "D: 所属",
    "E": "E: 潜在層",
    "F": "F: 企業PUSH",
    "G": "G: 潜在層_3分診断",
    "H": "H: 潜在層_年収診断",
    "I": "I: プロ講師_3分診断",
}

def extract_axis(ad_name: str) -> str:
    """NV_X... 形式から訴求軸(4文字目)を抽出。旧形式はOTHER。"""
    if not isinstance(ad_name, str):
        return "OTHER"
    m = re.match(r"^[NE][VPM]_([A-I])", ad_name)
    if m:
        return m.group(1)
    return "OTHER"

# ── BQクエリ ─────────────────────────────────────────────
SQL_CA = """
WITH agg AS (
  SELECT
    ad_name,
    SUM(spend)       AS spend,
    SUM(purchase)    AS cv,
    SUM(link_clicks) AS link_clicks
  FROM `bigquery-jukust.CA_meta_rpt.v_CA_meta_ads_daily_report_with_scenario`
  GROUP BY ad_name
)
SELECT
  ad_name,
  spend,
  cv,
  link_clicks,
  SAFE_DIVIDE(spend, cv)          AS cpa,
  SAFE_DIVIDE(cv, link_clicks)    AS cvr
FROM agg
WHERE spend >= 10000
  AND cv > 0
  AND link_clicks > 0
"""

SQL_ST = """
WITH agg AS (
  SELECT
    ad_name,
    SUM(spend)                 AS spend,
    SUM(complete_registration) AS cv,
    SUM(link_clicks)           AS link_clicks
  FROM `bigquery-jukust.ST_meta_rpt.v_ST_meta_campaign_report`
  GROUP BY ad_name
)
SELECT
  ad_name,
  spend,
  cv,
  link_clicks,
  SAFE_DIVIDE(spend, cv)          AS cpa,
  SAFE_DIVIDE(cv, link_clicks)    AS cvr
FROM agg
WHERE spend >= 10000
  AND cv > 0
  AND link_clicks > 0
"""

# ── データ取得 ────────────────────────────────────────────
print("BigQueryからデータ取得中...")

df_ca = client.query(SQL_CA).to_dataframe()
df_ca["brand"] = "CA"
print(f"CA: {len(df_ca)} 広告")

df_st = client.query(SQL_ST).to_dataframe()
df_st["brand"] = "ST"
print(f"ST: {len(df_st)} 広告")

df = pd.concat([df_ca, df_st], ignore_index=True)
df["axis"] = df["ad_name"].apply(extract_axis)

# 訴求軸ラベル付与
df["axis_label"] = df["axis"].map(AXIS_LABELS).fillna(df["axis"])

print(f"\n全広告数: {len(df)}")
print("\n訴求軸別 広告数:")
axis_counts = df.groupby("axis_label").size().sort_values(ascending=False)
for k, v in axis_counts.items():
    print(f"  {k}: {v}本")

# ── 回帰分析関数 ──────────────────────────────────────────
def run_regression(x: np.ndarray, y: np.ndarray):
    """OLS回帰。slope, intercept, r2, p_value を返す。"""
    if len(x) < 3:
        return None
    slope, intercept, r, p, se = stats.linregress(x, y)
    return {
        "slope": slope,
        "intercept": intercept,
        "r2": r ** 2,
        "p_value": p,
        "n": len(x),
    }

# ── 回帰実行・サマリ作成 ──────────────────────────────────
axes_target = [a for a in df["axis"].unique() if a != "OTHER"]
results = []

for axis in sorted(axes_target):
    sub = df[df["axis"] == axis].copy()
    label = AXIS_LABELS.get(axis, axis)
    n = len(sub)

    # CVR回帰
    reg_cvr = run_regression(sub["spend"].values, sub["cvr"].values)
    # CPA回帰
    reg_cpa = run_regression(sub["spend"].values, sub["cpa"].values)

    row = {
        "axis": axis,
        "axis_label": label,
        "n": n,
        "spend_mean": sub["spend"].mean(),
        "cvr_mean": sub["cvr"].mean(),
        "cpa_mean": sub["cpa"].mean(),
    }
    if reg_cvr:
        row.update({
            "cvr_slope": reg_cvr["slope"],
            "cvr_r2": reg_cvr["r2"],
            "cvr_p": reg_cvr["p_value"],
        })
    if reg_cpa:
        row.update({
            "cpa_slope": reg_cpa["slope"],
            "cpa_r2": reg_cpa["r2"],
            "cpa_p": reg_cpa["p_value"],
        })
    results.append(row)

df_result = pd.DataFrame(results)

# ── コンソール出力 ────────────────────────────────────────
print("\n" + "=" * 70)
print("回帰分析サマリ（訴求軸別）")
print("=" * 70)
print(f"{'訴求軸':<22} {'n':>4} {'spend平均':>10} {'CVR平均':>8} {'CPA平均':>10} {'CVR R2':>7} {'CVR p':>8} {'CPA R2':>7} {'CPA p':>8}")
print("-" * 90)
for _, row in df_result.iterrows():
    cvr_r2 = f"{row.get('cvr_r2', float('nan')):.3f}" if pd.notna(row.get("cvr_r2")) else "  N/A "
    cvr_p  = f"{row.get('cvr_p', float('nan')):.3f}" if pd.notna(row.get("cvr_p")) else "  N/A "
    cpa_r2 = f"{row.get('cpa_r2', float('nan')):.3f}" if pd.notna(row.get("cpa_r2")) else "  N/A "
    cpa_p  = f"{row.get('cpa_p', float('nan')):.3f}" if pd.notna(row.get("cpa_p")) else "  N/A "
    print(
        f"{row['axis_label']:<22} {row['n']:>4} "
        f"{row['spend_mean']:>10,.0f} "
        f"{row['cvr_mean']:>8.4f} "
        f"{row['cpa_mean']:>10,.0f} "
        f"{cvr_r2:>7} {cvr_p:>8} "
        f"{cpa_r2:>7} {cpa_p:>8}"
    )

# ── 散布図+回帰直線 ───────────────────────────────────────
try:
    import japanize_matplotlib
    japanize_matplotlib.japanize()
except ImportError:
    print("\n[INFO] japanize-matplotlib未インストール。日本語ラベルは英語にフォールバック。")
    AXIS_LABELS_EN = {k: v.replace("安心","Anshin").replace("承認","Shonin")
                     .replace("自己実現","Jiko").replace("所属","Shozoku")
                     .replace("潜在層","Senzai").replace("企業","Kigyou")
                     .replace("診断","Check").replace("プロ講師","Pro")
                     .replace("年収","Income") for k, v in AXIS_LABELS.items()}

fig_cols = 3
valid_axes = [r["axis"] for _, r in df_result.iterrows() if r["n"] >= 3]
n_axes = len(valid_axes)

if n_axes > 0:
    # --- CVR散布図 ---
    n_rows = (n_axes + fig_cols - 1) // fig_cols
    fig_cvr, axes_cvr = plt.subplots(n_rows, fig_cols, figsize=(15, 4 * n_rows))
    axes_cvr = np.array(axes_cvr).flatten()

    for i, axis in enumerate(valid_axes):
        sub = df[df["axis"] == axis]
        ax = axes_cvr[i]
        colors = ["#2196F3" if b == "CA" else "#FF5722" for b in sub["brand"]]
        ax.scatter(sub["spend"] / 10000, sub["cvr"] * 100, c=colors, alpha=0.7, s=50)

        reg = run_regression(sub["spend"].values, sub["cvr"].values)
        if reg:
            x_range = np.linspace(sub["spend"].min(), sub["spend"].max(), 100)
            y_fit = reg["slope"] * x_range + reg["intercept"]
            ax.plot(x_range / 10000, y_fit * 100, "r--", linewidth=1.5)
            sig = "**" if reg["p_value"] < 0.05 else ("*" if reg["p_value"] < 0.1 else "")
            ax.set_title(f"{AXIS_LABELS.get(axis, axis)}\nR²={reg['r2']:.3f}  p={reg['p_value']:.3f}{sig}  n={reg['n']}", fontsize=9)

        ax.set_xlabel("広告費 (万円)", fontsize=8)
        ax.set_ylabel("CVR (%)", fontsize=8)
        ax.tick_params(labelsize=7)

    # 凡例
    patch_ca = mpatches.Patch(color="#2196F3", label="CA")
    patch_st = mpatches.Patch(color="#FF5722", label="ST")
    fig_cvr.legend(handles=[patch_ca, patch_st], loc="upper right", fontsize=9)

    for j in range(i + 1, len(axes_cvr)):
        axes_cvr[j].set_visible(False)

    fig_cvr.suptitle("広告費 vs CVR（訴求軸別回帰分析）", fontsize=13, y=1.01)
    plt.tight_layout()
    out_cvr = "scripts/data/regression_cvr.png"
    plt.savefig(out_cvr, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n[保存] {out_cvr}")

    # --- CPA散布図 ---
    fig_cpa, axes_cpa = plt.subplots(n_rows, fig_cols, figsize=(15, 4 * n_rows))
    axes_cpa = np.array(axes_cpa).flatten()

    for i, axis in enumerate(valid_axes):
        sub = df[df["axis"] == axis]
        ax = axes_cpa[i]
        colors = ["#2196F3" if b == "CA" else "#FF5722" for b in sub["brand"]]
        ax.scatter(sub["spend"] / 10000, sub["cpa"], c=colors, alpha=0.7, s=50)

        reg = run_regression(sub["spend"].values, sub["cpa"].values)
        if reg:
            x_range = np.linspace(sub["spend"].min(), sub["spend"].max(), 100)
            y_fit = reg["slope"] * x_range + reg["intercept"]
            ax.plot(x_range / 10000, y_fit, "r--", linewidth=1.5)
            sig = "**" if reg["p_value"] < 0.05 else ("*" if reg["p_value"] < 0.1 else "")
            ax.set_title(f"{AXIS_LABELS.get(axis, axis)}\nR²={reg['r2']:.3f}  p={reg['p_value']:.3f}{sig}  n={reg['n']}", fontsize=9)

        ax.set_xlabel("広告費 (万円)", fontsize=8)
        ax.set_ylabel("CPA (円)", fontsize=8)
        ax.tick_params(labelsize=7)

    fig_cpa.legend(handles=[patch_ca, patch_st], loc="upper right", fontsize=9)

    for j in range(i + 1, len(axes_cpa)):
        axes_cpa[j].set_visible(False)

    fig_cpa.suptitle("広告費 vs CPA（訴求軸別回帰分析）", fontsize=13, y=1.01)
    plt.tight_layout()
    out_cpa = "scripts/data/regression_cpa.png"
    plt.savefig(out_cpa, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[保存] {out_cpa}")

# ── CSV保存 ───────────────────────────────────────────────
out_csv = "scripts/data/regression_summary.csv"
df_result.to_csv(out_csv, index=False, encoding="utf-8-sig")
print(f"[保存] {out_csv}")

# 広告レベルの全データも保存
out_detail = "scripts/data/regression_detail.csv"
df[["brand", "ad_name", "axis", "axis_label", "spend", "cv", "link_clicks", "cvr", "cpa"]].to_csv(
    out_detail, index=False, encoding="utf-8-sig"
)
print(f"[保存] {out_detail}")

print("\n完了。")
