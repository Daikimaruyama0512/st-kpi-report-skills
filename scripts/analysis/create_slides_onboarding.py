"""
STアフェニティチーム オンボーディングガイド - Google Slides生成
対象プレゼンテーション: 1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0
必要: pip install requests google-auth google-auth-oauthlib
"""
import json
import requests as req
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = "/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
PRES_ID = "1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0"

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/bigquery",
]

# Slide dimensions in EMU (16:9 standard)
SLIDE_W = 9144000
SLIDE_H = 5143500

# Brand colors as RGB fractions
def rgb(r, g, b):
    return {"red": r / 255, "green": g / 255, "blue": b / 255}

ORANGE = rgb(255, 112, 25)
WHITE  = rgb(255, 255, 255)
DARK   = rgb(30, 30, 30)
CREAM_LIGHT = rgb(255, 240, 220)
BLUE_LIGHT  = rgb(220, 235, 255)
GREEN_LIGHT = rgb(220, 255, 230)
ORANGE_SUB  = rgb(255, 230, 200)


# ── Auth ──────────────────────────────────────────────────────────────
def get_headers():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }


# ── API call ──────────────────────────────────────────────────────────
def batch_update(H, requests_list):
    url = f"https://slides.googleapis.com/v1/presentations/{PRES_ID}:batchUpdate"
    r = req.post(url, headers=H, json={"requests": requests_list})
    if not r.ok:
        print("Error:", r.status_code)
        print(r.text[:800])
        r.raise_for_status()
    return r.json()


# ── Low-level request builders ────────────────────────────────────────
def pt(n):
    return {"magnitude": n, "unit": "PT"}

def emu_size(w, h):
    return {
        "width":  {"magnitude": w, "unit": "EMU"},
        "height": {"magnitude": h, "unit": "EMU"},
    }

def emu_transform(x, y):
    return {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}

def create_slide_req(sid, idx):
    return {
        "createSlide": {
            "objectId": sid,
            "insertionIndex": idx,
            "slideLayoutReference": {"predefinedLayout": "BLANK"},
        }
    }

def set_bg_req(sid, color):
    return {
        "updatePageProperties": {
            "objectId": sid,
            "pageProperties": {
                "pageBackgroundFill": {"solidFill": {"color": {"rgbColor": color}}}
            },
            "fields": "pageBackgroundFill",
        }
    }

def create_textbox_req(oid, slide_id, x, y, w, h):
    return {
        "createShape": {
            "objectId": oid,
            "shapeType": "TEXT_BOX",
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": emu_size(w, h),
                "transform": emu_transform(x, y),
            },
        }
    }

def insert_text_req(oid, text):
    return {"insertText": {"objectId": oid, "insertionIndex": 0, "text": text}}

def text_style_req(oid, font_size=18, color=None, bold=False):
    return {
        "updateTextStyle": {
            "objectId": oid,
            "textRange": {"type": "ALL"},
            "style": {
                "bold": bold,
                "fontSize": pt(font_size),
                "foregroundColor": {"opaqueColor": {"rgbColor": color or DARK}},
            },
            "fields": "bold,fontSize,foregroundColor",
        }
    }

def para_style_req(oid, align="START"):
    return {
        "updateParagraphStyle": {
            "objectId": oid,
            "textRange": {"type": "ALL"},
            "style": {"alignment": align},
            "fields": "alignment",
        }
    }

def shape_bg_req(oid, color, content_align="MIDDLE"):
    return {
        "updateShapeProperties": {
            "objectId": oid,
            "shapeProperties": {
                "contentAlignment": content_align,
                "shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": color}}},
            },
            "fields": "contentAlignment,shapeBackgroundFill",
        }
    }

def delete_req(oid):
    return {"deleteObject": {"objectId": oid}}


# ── Helpers ────────────────────────────────────────────────────────────
def header_bar(sid, hid, title_text):
    """Orange header bar + white bold title centered."""
    return [
        create_textbox_req(hid, sid, 0, 0, SLIDE_W, 700000),
        shape_bg_req(hid, ORANGE),
        insert_text_req(hid, title_text),
        text_style_req(hid, font_size=28, color=WHITE, bold=True),
        para_style_req(hid, align="CENTER"),
    ]

def content_box(sid, cid, text, font_size=17):
    """Standard content text box below header."""
    return [
        create_textbox_req(cid, sid, 457200, 820000, 8229600, 4200000),
        insert_text_req(cid, text),
        text_style_req(cid, font_size=font_size, color=DARK),
    ]


# ── Slide builders ─────────────────────────────────────────────────────
def slide01_title(idx):
    sid = "slide01"
    return [
        create_slide_req(sid, idx),
        set_bg_req(sid, ORANGE),
        create_textbox_req("s01_title", sid, 457200, 1200000, 8229600, 2200000),
        insert_text_req("s01_title", "STアフェニティチーム\nオンボーディングガイド"),
        text_style_req("s01_title", font_size=40, color=WHITE, bold=True),
        para_style_req("s01_title", align="CENTER"),
        create_textbox_req("s01_sub", sid, 457200, 3600000, 8229600, 600000),
        insert_text_req("s01_sub", "2026年8月　新メンバー向けガイド"),
        text_style_req("s01_sub", font_size=20, color=ORANGE_SUB),
        para_style_req("s01_sub", align="CENTER"),
    ]

def slide02_agenda(idx):
    sid = "slide02"
    agenda_text = (
        "① ST概要 ─ 事業モデル・ターゲット・アフェニティの役割\n"
        "② KPI体系 ─ KPIツリー・タイムラグの理解\n"
        "③ 業務フロー ─ 週次・月次ルーティン\n"
        "④ 使用ツール ─ Meta / Canva / ペライチ / Claude Code\n"
        "⑤ LP・クリエイティブガイド ─ 制作基準・命名規則\n"
        "⑥ 分析・KPI報告 ─ 評価の型・BigQuery"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s02_h", "AGENDA")
        + content_box(sid, "s02_c", agenda_text, font_size=20)
    )

def slide03_overview(idx):
    sid = "slide03"
    text = (
        "事業概要\n"
        "・塾講師ステーション（ST）: 塾・家庭教師バイト専門の求人サイト\n"
        "・ビジネスモデル: 掲載課金（塾側が掲載費を支払う。ユーザー無料）\n"
        "・ターゲット: 大学生 18〜22歳（塾講師バイトを探している層）\n\n"
        "アフェニティチームの役割\n"
        "・Meta広告 / Google広告の運用（クリエイティブ・LP・入稿・分析）\n"
        "・KPIフロー: IMP → CTR → LP流入 → LINE登録 → 応募 → 採用\n"
        "・目標: LINE登録CPA・応募CPA・採用CPAの最適化\n\n"
        "他部署・外部との連携\n"
        "・営業チーム: 掲載企業との関係・掲載数管理\n"
        "・ペライチ担当: LP公開・URL管理\n"
        "・外部: Canva Pro / Meta広告審査"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s03_h", "① ST概要")
        + content_box(sid, "s03_c", text, font_size=16)
    )

def slide04_personas(idx):
    sid = "slide04"
    col_w = 2743200
    col_h = 3900000
    margin = 228600
    top_y = 830000

    p1_text = "タイパ重視\n（積極探し）\n\n・すぐ働きたい\n・条件（時給・距離）で選ぶ\n・登録→即応募が多い\n\n▶ 訴求軸: ベネフィット型\n「30秒で診断・すぐ応募」"
    p2_text = "ミスマッチ回避\n（単願・慎重）\n\n・1社に絞って慎重に決めたい\n・「本当に合うか」が不安\n・口コミ・評判を重視\n\n▶ 訴求軸: 共感型\n「合う塾、見つかる」"
    p3_text = "ミスマッチ回避\n（併願・比較中）\n\n・複数社を比較検討中\n・差別化ポイントで判断する\n・競合も見ている\n\n▶ 訴求軸: 差別化型\n「他と比べてみて」"

    reqs = [create_slide_req(sid, idx)]
    reqs += header_bar(sid, "s04_h", "ターゲット 3ペルソナ（大学生 18〜22歳）")

    for i, (pid, text, bg) in enumerate([
        ("s04_p1", p1_text, CREAM_LIGHT),
        ("s04_p2", p2_text, BLUE_LIGHT),
        ("s04_p3", p3_text, GREEN_LIGHT),
    ]):
        x = margin + i * (col_w + margin)
        reqs += [
            create_textbox_req(pid, sid, x, top_y, col_w, col_h),
            shape_bg_req(pid, bg, content_align="TOP"),
            insert_text_req(pid, text),
            text_style_req(pid, font_size=15, color=DARK),
        ]

    return reqs

def slide05_kpi(idx):
    sid = "slide05"
    text = (
        "KPIツリー（上流 → 下流）\n\n"
        "IMP（インプレッション数）\n"
        "  ↓  CTR（クリック率）\n"
        "LP流入数\n"
        "  ↓  LP→LINE CVR（LINE登録率）← 主要最適化ポイント\n"
        "LINE登録数  ★ メインKPI\n"
        "  ↓  LINE→応募率\n"
        "応募数\n"
        "  ↓  採用率\n"
        "採用数\n\n"
        "主要KPI定義\n"
        "・LINE登録CPA  = 広告費 ÷ LINE登録数\n"
        "・応募CPA      = 広告費 ÷ 応募数\n"
        "・採用CPF      = 広告費 ÷ 採用数\n"
        "・LP→LINE CVR  = LINE登録数 ÷ LP流入数 × 100（%）"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s05_h", "② KPI体系")
        + content_box(sid, "s05_c", text, font_size=16)
    )

def slide06_timelag(idx):
    sid = "slide06"
    return [
        create_slide_req(sid, idx),
        set_bg_req(sid, ORANGE),
        create_textbox_req("s06_main", sid, 457200, 500000, 8229600, 2400000),
        insert_text_req("s06_main", "LINE登録 → 面談申込\n中央値 40日のタイムラグ"),
        text_style_req("s06_main", font_size=36, color=WHITE, bold=True),
        para_style_req("s06_main", align="CENTER"),
        create_textbox_req("s06_sub", sid, 457200, 3050000, 8229600, 1300000),
        insert_text_req("s06_sub",
            "直近40日以内のCV数は「過小評価」として扱う\n"
            "評価軸は 直近90日累計 ベースで判断する"),
        text_style_req("s06_sub", font_size=24, color=WHITE),
        para_style_req("s06_sub", align="CENTER"),
        create_textbox_req("s06_note", sid, 457200, 4450000, 8229600, 550000),
        insert_text_req("s06_note", "週次数値は速度感チェックのみ（評価指標として使わない）"),
        text_style_req("s06_note", font_size=18, color=ORANGE_SUB),
        para_style_req("s06_note", align="CENTER"),
    ]

def slide07_workflow(idx):
    sid = "slide07"
    text = (
        "週次ルーティン\n"
        "・月曜: 先週KPI集計 → 週次報告（Claude Code /kpi-report スキル活用）\n"
        "・火〜木: 広告運用（クリエイティブ入稿・LP改善・BQ分析）\n"
        "・金曜: 翌週クリエイティブ準備・Canva制作・命名規則チェック\n\n"
        "月次ルーティン\n"
        "・月初: 先月月次KPI報告 → 上長報告\n"
        "・中旬: A/Bテスト判定（CVR差+2pt & p<0.05 が基準）\n"
        "・月末: 翌月クリエイティブ・シナリオ設計（/create-scenario）\n\n"
        "承認フロー\n"
        "・予算10%超過の変更 → 上長確認必須（運用管理SS記録）\n"
        "・新クリエイティブ入稿 → 命名規則確認 → 入稿\n"
        "・LP改変（FV変更等） → A/Bテスト計画書に記録"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s07_h", "③ 業務フロー")
        + content_box(sid, "s07_c", text, font_size=16)
    )

def slide08_tools(idx):
    sid = "slide08"
    text = (
        "ツール一覧\n"
        "Meta広告管理画面   広告入稿・キャンペーン設定・配信分析\n"
        "Canva              クリエイティブ制作（動画・ストーリーズ）\n"
        "ペライチ            LP公開・管理（HTML埋め込み対応）\n"
        "Claude Code         LP作成・コピー生成・KPI報告 自動化\n"
        "BigQuery            広告データ分析・SQLクエリ実行\n"
        "スプレッドシート     KPIデータ参照・週次報告（集計さん）\n\n"
        "Claude Codeスキルの使い方（チャットで入力するだけ）\n"
        "/kpi-report         週次・月次KPI報告を自動生成\n"
        "/lp-create          LP新規作成（競合分析 → HTML生成）\n"
        "/lp-copy-variants   FVキャッチコピーバリエーション生成\n"
        "/create-scenario    Meta広告シナリオ設計"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s08_h", "④ 使用ツール")
        + content_box(sid, "s08_c", text, font_size=16)
    )

def slide09_lp(idx):
    sid = "slide09"
    text = (
        "LP構成（上から）\n"
        "① FV: キャッチコピー + CTAボタン（LINE登録）\n"
        "② STATS: 実績数値（1.5万件 / 2.7万人 / 30秒）\n"
        "③ 3ステップ: LINE登録 → 診断 → 応募\n"
        "④ 口コミ・体験談\n"
        "⑤ 選ばれる理由（差別化ポイント）\n"
        "⑥ ラストCTA\n\n"
        "ブランドカラー\n"
        "・メインオレンジ: #FF7019\n"
        "・LINEグリーン: #06C755\n"
        "・背景クリーム: #FAE2D1\n\n"
        "A/Bテストの進め方\n"
        "・指標: LINE登録CVR（メイン）\n"
        "・期間: 2週間・同一クリエイティブで配信\n"
        "・判定基準: CVR差 +2pt かつ p<0.05 → 勝ち案を採用\n"
        "・記録: A/Bテスト計画書SSに必ず記録"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s09_h", "⑤ LPガイド")
        + content_box(sid, "s09_c", text, font_size=15)
    )

def slide10_creative(idx):
    sid = "slide10"
    text = (
        "5つの訴求軸\n"
        "・課題解決型: ペインを言語化「合う塾が見つからない?」→ ミスマッチ回避層\n"
        "・ベネフィット型: 得られる未来「収入UP・就活ガクチカ」→ タイパ重視層\n"
        "・数字型: 実績・信頼「1.5万件・2.7万人・30秒」→ 慎重派\n"
        "・共感型: 感情に寄り添う「その気持ち、わかる」→ 単願ミスマッチ回避\n"
        "・差別化型: 競合との違い「他のバイトと違う理由」→ 併願型\n\n"
        "シナリオ設計の型（動画広告）\n"
        "フック（0〜3秒）: 共感・問いかけで止める\n"
        "ボディ: 問題提起 → STが解決 → 実績で信頼\n"
        "CTA: 「LINE登録して」「適職診断してみて」\n\n"
        "命名規則（必ず準拠）\n"
        "形式: [訴求軸]_[動画の型]_[詳細]_[日付]\n"
        "例: BN_TS_塾バイトデビュー_250801\n"
        "→ knowledge/creative/meta-ads-naming.md を必ず確認"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s10_h", "⑤ クリエイティブガイド")
        + content_box(sid, "s10_c", text, font_size=15)
    )

def slide11_analytics(idx):
    sid = "slide11"
    text = (
        "分析の型（この順序を守る）\n"
        "1. 結論（1〜2行で即答）\n"
        "2. 根拠データ（表: ad_name / spend / purchase / CPA）\n"
        "3. 推奨アクション（優先度付き・3件以内）\n\n"
        "クリエイティブ評価手順\n"
        "・評価期間: 直近90日累計（週次は速度感チェックのみ）\n"
        "・直近90日の広告別 CPA = SAFE_DIVIDE(spend, purchase)\n"
        "・spend >= 1万円のみ評価対象（小額は除外）\n"
        "・命名規則で訴求軸・動画の型を分類してパターン分析\n\n"
        "BigQuery主要情報\n"
        "・プロジェクト: bigquery-jukust\n"
        "・認証: OAuth（token.json）※サービスアカウント禁止\n"
        "・主要ビュー: ST_meta_daily_view / ST_meta_creative_90days\n\n"
        "週次KPI報告\n"
        "・Claude Code で /kpi-report と入力するだけ\n"
        "・BigQuery自動クエリ → スプレッドシート書き込み → 報告文生成"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s11_h", "⑥ 分析・KPI報告")
        + content_box(sid, "s11_c", text, font_size=15)
    )

def slide12_checklist(idx):
    sid = "slide12"
    text = (
        "理解レベル（まず身につける）\n"
        "□ ST事業・掲載課金モデルを説明できる\n"
        "□ 3ペルソナの違いと訴求軸を言える\n"
        "□ KPIツリー（IMP→採用）を把握している\n"
        "□ タイムラグ（中央値40日・90日評価）を理解している\n\n"
        "基礎レベル（1週間以内）\n"
        "□ 各ツール（Meta/Canva/ペライチ）にログイン・基本操作できる\n"
        "□ 命名規則マスタ（meta-ads-naming.md）を読んだ\n"
        "□ 週次KPI報告を/kpi-reportで1回作成した\n"
        "□ 既存LPのFVキャッチコピーを把握している\n\n"
        "応用レベル（1ヶ月以内）\n"
        "□ A/Bテストを設計・実行・判定できる\n"
        "□ BigQueryでクリエイティブ評価クエリを書ける\n"
        "□ Claude Codeスキルを自力で使いこなせる\n"
        "□ 週次報告を上長に提出できる"
    )
    return (
        [create_slide_req(sid, idx)]
        + header_bar(sid, "s12_h", "チェックリスト")
        + content_box(sid, "s12_c", text, font_size=15)
    )

def slide13_summary(idx):
    sid = "slide13"
    return [
        create_slide_req(sid, idx),
        set_bg_req(sid, ORANGE),
        create_textbox_req("s13_main", sid, 457200, 600000, 8229600, 2200000),
        insert_text_req("s13_main", "KPIを理解して、クリエイティブと\nLPでCVRを上げていく仕事"),
        text_style_req("s13_main", font_size=34, color=WHITE, bold=True),
        para_style_req("s13_main", align="CENTER"),
        create_textbox_req("s13_sub", sid, 457200, 2950000, 8229600, 1300000),
        insert_text_req("s13_sub",
            "わからないことはClaude Codeに聞いて。\n"
            "スキルとknowledgeが助けてくれる。"),
        text_style_req("s13_sub", font_size=22, color=ORANGE_SUB),
        para_style_req("s13_sub", align="CENTER"),
        create_textbox_req("s13_links", sid, 457200, 4350000, 8229600, 600000),
        insert_text_req("s13_links",
            "スプレッドシート版: 1UakK5ig5spCTQmgdrd32XsJjiHLyAmGhymb1B5o-i8s  |  BigQuery: bigquery-jukust"),
        text_style_req("s13_links", font_size=13, color=WHITE),
        para_style_req("s13_links", align="CENTER"),
    ]


# ── Main ───────────────────────────────────────────────────────────────
def main():
    H = get_headers()

    # 既存スライドを確認
    r = req.get(
        f"https://slides.googleapis.com/v1/presentations/{PRES_ID}",
        headers=H
    )
    r.raise_for_status()
    pres = r.json()
    existing = [s["objectId"] for s in pres.get("slides", [])]
    print(f"既存スライド数: {len(existing)} → 削除予定: {existing}")

    base = len(existing)  # 新スライドはexistingの後に挿入

    all_requests = []
    all_requests += slide01_title(base + 0)
    all_requests += slide02_agenda(base + 1)
    all_requests += slide03_overview(base + 2)
    all_requests += slide04_personas(base + 3)
    all_requests += slide05_kpi(base + 4)
    all_requests += slide06_timelag(base + 5)
    all_requests += slide07_workflow(base + 6)
    all_requests += slide08_tools(base + 7)
    all_requests += slide09_lp(base + 8)
    all_requests += slide10_creative(base + 9)
    all_requests += slide11_analytics(base + 10)
    all_requests += slide12_checklist(base + 11)
    all_requests += slide13_summary(base + 12)

    # 既存の空白スライドを削除
    for sid in existing:
        all_requests.append(delete_req(sid))

    print(f"実行リクエスト数: {len(all_requests)}")
    result = batch_update(H, all_requests)
    print(f"完了: {len(result.get('replies', []))} replies")
    print(f"\nURL: https://docs.google.com/presentation/d/{PRES_ID}/edit")


if __name__ == "__main__":
    main()
