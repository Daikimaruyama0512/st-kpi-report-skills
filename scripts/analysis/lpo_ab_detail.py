# LPO ABテスト: 分析詳細・仮説背景を追記
import sys, io
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
SPREADSHEET_ID = "1JD-Sj6Kf2yWFOTrVfV9QcwUzDJ0DVum1EwFYLiXi9Lc"
SHEET_GID = "468902428"

def get_creds():
    return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

def find_sheet_name(sheets):
    meta = sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for s in meta.get("sheets", []):
        if str(s["properties"]["sheetId"]) == SHEET_GID:
            return s["properties"]["title"]
    return None

def get_last_row(sheets, sheet_name):
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!A:A"
    ).execute()
    return len(result.get("values", []))

def build_detail_rows():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    rows.append([""])
    rows.append(["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"])
    rows.append([f"■ 分析詳細・仮説背景（{now} 追記）"])
    rows.append(["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"])
    rows.append([""])

    # ── 分析コンテキスト ──
    rows.append(["【分析コンテキスト】"])
    rows.append(["▼ このABテストが測定しようとしていること"])
    rows.append(["",
        "同一クリエイティブ（動画・コピー）でLPだけを変更したときに、CVR（LINE登録率）がどう変わるかを測る。",
        "クリエイティブの良し悪しとLPの良し悪しを切り分けることが目的。",
        "LP-Aは既存のブランド診断LP（診断訴求中心）、LP-Bはメインビジュアルと実績数字を追加した改善版。"
    ])
    rows.append([""])
    rows.append(["▼ 現状のデータ制約"])
    rows.append(["",
        "夏の予定LP-B: データなし（配信実績0）→ 比較不能",
        "夏期講習LP-B: spend ¥18,990・CV=0 → ¥10,000以上だが、CVが0のため離脱率100%とも読める。",
        "ただし夏期講習LP-BのCVが0なのは「LPが悪い」だけでなく「母数が少なすぎて確率的に0が出た」可能性が高い。",
        "→ ¥30,000以上・最低2週間配信しないと統計的に意味のある判断はできない。"
    ])
    rows.append([""])

    # ── 仮説詳細 ──
    rows.append(["【仮説の詳細背景】"])
    rows.append([""])

    rows.append(["仮説1: LP-AはFVにビジュアルがなく「診断」への動機づけが弱い"])
    rows.append(["背景・説明",
        "LP-AのFVはテキストのみ（「あなたに合う塾はどこ？ 塾ブランド診断」）。",
        "塾バイト初挑戦の学生にとって、テキストだけでは「自分がここで求職できる」というイメージが湧きにくい。",
        "LP-Bはスマートフォンを手に笑顔の女性写真を使うことで「自分が使うシーン」を可視化している。",
        "Webランディングページの研究では、人物写真（特に笑顔）がCVRを高めるケースが多い（感情的接続効果）。",
        "LP-Aの場合、FVの段階でスクロールせず離脱するユーザーが多い可能性が高い。"
    ])
    rows.append(["確認方法", "ヒートマップツール（Hotjar等）を使ってスクロール率・クリック率を取ると定量化できる。"])
    rows.append([""])

    rows.append(["仮説2: 「診断を始める」CTAはベネフィットが不明確で押しづらい"])
    rows.append(["背景・説明",
        "LP-AのCTA文言「診断を始める」は行動（何をするか）は伝えているが、結果（何が得られるか）が不明。",
        "LP-Bの「自分に合う塾がわかる 塾ブランド診断」はCTA内でベネフィット（自分に合う塾がわかる）を先に提示している。",
        "行動経済学の観点では、ベネフィットを先に示すことでクリックへの心理的障壁が下がる。",
        "「診断」というワードは一般的にやや敷居が高いイメージ（テスト・評価される感覚）があり、",
        "LP-Bの「自分に合う塾がわかる」という言い方は診断を「損しない行動」として再フレーミングしている点が優れている。"
    ])
    rows.append(["確認方法", "CTAのクリック率（CTA直下のクリックヒートマップ）で直接測定できる。"])
    rows.append([""])

    rows.append(["仮説3: LP-AはLINE登録への心理的ブロックが未解消"])
    rows.append(["背景・説明",
        "LINE登録に対してユーザーが持ちやすい懸念: 個人情報が取られる・しつこい通知が来る・退会が面倒。",
        "LP-Bは「LINEで簡単登録3分・個人情報不要」を明示することで、これらのブロックを先回りで解除している。",
        "特に「個人情報不要」は強力で、名前・電話番号等の入力を求められないという安心感が即座に伝わる。",
        "LP-Aはこのような安心感テキストが一切ない。初訪問ユーザーがLINE登録ボタン前で躊躇して離脱するリスクが高い。",
        "塾バイト求職者層（大学生）はLINEへの登録自体は抵抗が少ないが、それでも「何が起きるか」の不安解消は効果的。"
    ])
    rows.append(["確認方法", "CTAボタン到達後の離脱率をヒートマップやGA4イベントで確認。"])
    rows.append([""])

    rows.append(["仮説4: LP-Bの実績数字（1.5万件/2.7万人）が信頼感を底上げしている"])
    rows.append(["背景・説明",
        "「1.5万件の掲載求人数」「2.7万人の年間利用者」「3分でLINE登録」という3つの数字をFVに配置。",
        "初訪問ユーザーにとって、サービスの実績数字は信頼性の代替指標として機能する（Social Proof）。",
        "特に求職系サービスでは「このサービスが使われているかどうか」が重要な判断基準になる。",
        "LP-Aにはこの種の数字が一切なく、ブランド力のみで判断させている状態。",
        "「3分」という時間表示は短さを強調することで行動コストが小さいと感じさせる効果がある。",
        "※ただしこの仮説は論理的推測（★）。数字があれば必ずCVR向上するわけではなく、数字の信頼性・見せ方にも依存する。"
    ])
    rows.append(["確認方法", "数字部分のアイトラッキングやA/Bテスト（数字あり/なし）で確認可能。"])
    rows.append([""])

    rows.append(["仮説5: 現状データは統計的に不十分で判断不能"])
    rows.append(["背景・説明",
        "ABテストで統計的に有意な差を検出するには、十分なサンプルサイズが必要。",
        "一般的なCVRが1〜2%の場合、95%信頼区間で差を検出するには各LPに最低500〜1000クリックが必要。",
        "現在のLP-B（夏期講習）はspend ¥18,990でCV=0。これは「LP-Bが悪い」証拠ではなく「データ不足」。",
        "たとえばCVR=1%のLPで100クリックしても、確率的にCV=0が出る可能性は約37%（e^-1 ≈ 0.37）ある。",
        "→ ¥30,000以上（推定150〜200クリック以上）まで待ってから判断することが原則。",
        "現時点でLP-Bを「効果なし」と判断してオフにするのは早計で、データの機会損失になる。"
    ])
    rows.append(["確認方法", "¥30,000消化後に両LPのCVR・CPA・CV数を比較し、カイ二乗検定または比率の差の検定で判定。"])
    rows.append([""])

    # ── LP別強み・弱みサマリー ──
    rows.append(["【LP別 強み・弱みサマリー】"])
    rows.append(["", "LP-A（brandtest）", "LP-B（brandtest_m2）"])
    rows.append(["強み",
        "診断訴求がシンプル・ブランドロゴ直下でCTAが素早く目に入る",
        "メインビジュアルで感情的接続・実績数字で信頼感・安心感テキストで心理的ブロック解除"
    ])
    rows.append(["弱み",
        "ビジュアルなし・ベネフィット不明確なCTA・安心感テキスト不在・FVの情報量が少ない",
        "情報量が多くスクロール前の離脱ポイントが増える可能性・配信データが不十分で検証未完"
    ])
    rows.append(["向いているユーザー",
        "すでにブランド診断を知っていて「やってみよう」と思っているリターゲユーザー向き",
        "初訪問・塾バイト検討初期段階のコールドオーディエンス向き"
    ])
    rows.append([""])
    rows.append(["＊ LP-AはリタゲCVRは高い可能性があるため、用途に応じてLP使い分けも検討価値あり"])

    return rows

def main():
    creds  = get_creds()
    sheets = build("sheets", "v4", credentials=creds)

    sheet_name = find_sheet_name(sheets)
    if not sheet_name:
        print(f"シートGID {SHEET_GID} が見つかりません")
        sys.exit(1)
    print(f"対象シート: 「{sheet_name}」")

    last_row = get_last_row(sheets, sheet_name)
    print(f"既存データ: {last_row} 行 → {last_row + 1} 行目から追記")

    rows = build_detail_rows()

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!A{last_row + 1}",
        valueInputOption="USER_ENTERED",
        body={"values": rows}
    ).execute()
    print(f"「{sheet_name}」に追記完了（{len(rows)} 行）")

if __name__ == "__main__":
    main()
