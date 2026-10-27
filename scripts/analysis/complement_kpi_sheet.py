"""
スプレッドシート「分析・KPI報告」タブに欠落5セクションを追記する
書き込み先: 1UakK5ig5spCTQmgdrd32XsJjiHLyAmGhymb1B5o-i8s（gid=661700305）
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/presentations',
]

SHEET_ID   = "1UakK5ig5spCTQmgdrd32XsJjiHLyAmGhymb1B5o-i8s"
TAB_NAME   = "分析・KPI報告"

# ─────────────────────────────────────────
# 追記するコンテンツ（5セクション）
# 各行 = リスト。空行 = [] か [""]
# ─────────────────────────────────────────
ROWS = [
    [],
    ["■ LPオペレーション基本ルール"],
    ["項目", "内容"],
    ["CVポイント", "LINE友だち追加（lin.ee経由）"],
    ["LP評価指標", "LP-CVR（LINE追加クリック数 ÷ LP表示数）"],
    ["LP評価サイクル", "月次（クリエイティブ評価と同タイミング）"],
    ["改善トリガー", "応募CPA ¥30,000超 かつ 転換率<10% でLP起因を疑う"],
    ["A/Bテスト原則", "変数1つずつ変更・最低2週間 & 500表示以上で判定"],
    ["管理ファイル", "lp/line_meta_IG.html（Gitで管理）"],
    [],
    ["■ KPI目標値（ST_Meta広告）"],
    ["▼応募CPA"],
    ["状態", "基準", "対応"],
    ["良好", "¥20,000以下", "継続。予算引き上げを検討"],
    ["要観察", "¥20,001〜30,000", "クリエイティブ・LP改善を検討"],
    ["要見直し", "¥30,001〜40,000", "CTA配分・ナーチャリング改善を優先"],
    ["要停止検討", "¥40,001以上", "停止理由を明確化できなければ停止"],
    ["▼転換率（LINE登録→応募）"],
    ["状態", "基準"],
    ["良好", "15%以上"],
    ["要改善", "10〜14%"],
    ["緊急対応", "10%未満"],
    ["▼CPF（LINE登録単価）目安"],
    ["顕在層（ペルソナLP等）", "¥1,500〜3,000"],
    ["潜在層（気軽に診断等）", "¥700〜1,500"],
    ["▼クリエイティブ停止基準"],
    ["消化¥15,000超でCV0件", "→ 即停止"],
    ["出稿2日経過で消化¥1,000未満", "→ 停止"],
    [],
    ["■ Claude Code スキル使い分けガイド"],
    ["やりたいこと", "スキル / エージェント"],
    ["週次KPI報告を自動生成する", "kpi-report スキル"],
    ["シナリオを作る・修正する", "create-scenario スキル"],
    ["広告分析・クリエイティブ評価", "ads-analyst エージェント"],
    ["LPのコピーバリエーションを出す", "lp-copy-variants スキル"],
    ["LPをゼロから作る", "lp-create スキル"],
    ["スプレッドシートに書き込む", "write-sheet スキル"],
    ["分析結果をドキュメント化する", "gdoc スキル"],
    [],
    ["■ 分析→アクション フロー"],
    ["Step", "内容", "ツール"],
    ["1", "BigQueryで直近90日CPA確認（spend ≥ ¥10,000）", "Claude Code / BigQuery"],
    ["2", "停止判断（消化¥15,000超でCV0 → 即停止）", "Meta広告管理画面"],
    ["3", "予算調整（月10%以上の変更は事前確認必須）", "要承認"],
    ["4", "新クリエイティブ企画・シナリオ作成", "create-scenario スキル"],
    ["5", "LP改善が必要なら lp-copy-variants でコピー案を生成", "lp-copy-variants スキル"],
    ["▼指標別トラブルシューティング"],
    ["低下指標", "想定要因", "打ち手"],
    ["CTR低下", "クリエイティブの摩耗・インサイトのズレ", "訴求軸・動画の型を入れ替え"],
    ["CVR低下", "広告とLPの期待値ギャップ", "Meta〜LP〜LINEのメッセージ一貫性を確認"],
    ["IMP低下", "AIの過度な絞り込み・顕在層の枯渇", "ターゲット拡張・潜在層投資強化"],
    [],
    ["■ KPI理解チェックリスト（新メンバー確認用）"],
    ["チェック", "確認内容"],
    ["□", "90日評価・週次参考のルールを他者に説明できる"],
    ["□", "40日タイムラグを考慮した数値の読み方ができる"],
    ["□", "BigQueryでkpi-reportのクエリを自分で実行できた"],
    ["□", "kpi-reportスキルを一人で完走できた（試走済み）"],
    ["□", "応募CPAの良好/要観察/要見直し基準を言える（¥20,000 / ¥30,000 / ¥40,000）"],
    ["□", "LP-CVRとは何かを説明できる"],
    ["□", "どのスキルをどんな時に使うかを答えられる"],
]

def main():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    svc   = build("sheets", "v4", credentials=creds, cache_discovery=False)

    # 既存行数を確認
    existing = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"'{TAB_NAME}'",
    ).execute()
    current_rows = len(existing.get("values", []))
    print(f"既存行数: {current_rows}")

    # 追記（append は末尾の空でない行の次に書く）
    body = {"values": ROWS}
    resp = svc.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"'{TAB_NAME}'!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()

    updated_range = resp.get("updates", {}).get("updatedRange", "")
    updated_rows  = resp.get("updates", {}).get("updatedRows", 0)
    print(f"追記完了: {updated_rows} 行 → {updated_range}")
    print("ブラウザで確認してください:")
    print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid=661700305#gid=661700305")

if __name__ == "__main__":
    main()
