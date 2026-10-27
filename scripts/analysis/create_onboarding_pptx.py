#!/usr/bin/env python3
"""
STアフェニティチーム オンボーディングガイド PPTX生成スクリプト
必要: pip install python-pptx
出力: scripts/data/onboarding_affinity_2026.pptx
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
except ImportError:
    print("python-pptxが必要: pip install python-pptx")
    sys.exit(1)

# ── カラー ──
OG  = RGBColor(0xFF, 0x70, 0x19)   # メインオレンジ
OGL = RGBColor(0xFF, 0xE8, 0xD6)   # ライトオレンジ
DK  = RGBColor(0x1A, 0x1A, 0x2E)   # ダークネイビー
GY  = RGBColor(0x55, 0x55, 0x66)   # グレー
WH  = RGBColor(0xFF, 0xFF, 0xFF)   # 白
GN  = RGBColor(0x06, 0xC7, 0x55)   # LINEグリーン
LG  = RGBColor(0xF4, 0xF4, 0xF6)   # ライトグレー
BL  = RGBColor(0x4A, 0x90, 0xD9)   # ブルー
GR  = RGBColor(0x27, 0xAE, 0x60)   # グリーン
PU  = RGBColor(0x8B, 0x5C, 0xF6)   # パープル
CR  = RGBColor(0xFA, 0xE2, 0xD1)   # クリーム

FONT = "Hiragino Sans"
W  = Inches(13.33)
H  = Inches(7.5)
M  = Inches(0.5)
TH = Inches(1.15)   # タイトルバー高さ

# ─────────────────────────────────
# ヘルパー関数
# ─────────────────────────────────

def new_prs():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs

def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def _run(r, size, bold, color):
    r.font.name  = FONT
    r.font.size  = Pt(size)
    r.font.bold  = bold
    if color:
        r.font.color.rgb = color

def txb(slide, text, l, t, w, h,
        size=13, bold=False, color=None, align=PP_ALIGN.LEFT, wrap=True):
    """シンプルなテキストボックス（1段落）"""
    box = slide.shapes.add_textbox(l, t, w, h)
    tf  = box.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    _run(r, size, bold, color or DK)
    return box

def mlb(slide, lines, l, t, w, h, size=13):
    """複数行テキストボックス。▶/【/★ で始まる行は強調表示"""
    box = slide.shapes.add_textbox(l, t, w, h)
    tf  = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = line
        if line.startswith('▶'):
            _run(r, size + 1, True, OG)
        elif line.startswith('【') or line.startswith('★'):
            _run(r, size, True, DK)
        elif line == '':
            _run(r, size - 2, False, WH)  # 空行（高さ確保）
        else:
            _run(r, size, False, GY)
    return box

def rct(slide, l, t, w, h, fill=None, line_c=None, lw=1.5):
    """矩形"""
    shp = slide.shapes.add_shape(1, l, t, w, h)
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    else:
        shp.fill.background()
    if line_c:
        shp.line.color.rgb = line_c
        shp.line.width = Pt(lw)
    else:
        shp.line.fill.background()
    return shp

def title_bar(slide, title, badge=None, bg=OG):
    """オレンジのタイトルバー"""
    rct(slide, 0, 0, W, TH, fill=bg)
    if badge:
        txb(slide, badge,
            Inches(0.28), Inches(0.17), Inches(0.8), Inches(0.85),
            size=22, bold=True, color=WH, align=PP_ALIGN.CENTER)
        txb(slide, title,
            Inches(1.18), Inches(0.28), W - Inches(1.7), Inches(0.65),
            size=21, bold=True, color=WH)
    else:
        txb(slide, title,
            M, Inches(0.28), W - M * 2, Inches(0.65),
            size=24, bold=True, color=WH)

def add_tbl(slide, headers, rows, l, t, w, col_ws=None, rh=Inches(0.55)):
    """テーブル追加"""
    nr = len(rows) + 1
    nc = len(headers)
    shp = slide.shapes.add_table(nr, nc, l, t, w, rh * nr)
    tbl = shp.table
    if col_ws:
        for i, cw in enumerate(col_ws):
            tbl.columns[i].width = cw
    # ヘッダー行
    for ci, hdr in enumerate(headers):
        cell = tbl.cell(0, ci)
        cell.fill.solid()
        cell.fill.fore_color.rgb = OG
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = hdr
        _run(r, 12, True, WH)
    # データ行
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri + 1, ci)
            if ri % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LG
            else:
                cell.fill.background()
            p = cell.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = val
            _run(r, 11, False, GY)
    return tbl

def card(slide, l, t, w, h, header_text, items, hc=OG, hh=Inches(0.65), size=12):
    """カード型ボックス（ヘッダー色帯 + リスト）"""
    rct(slide, l, t, w, h, fill=LG)
    rct(slide, l, t, w, hh, fill=hc)
    txb(slide, header_text, l + Inches(0.1), t + Inches(0.1),
        w - Inches(0.2), hh - Inches(0.1),
        size=14, bold=True, color=WH, align=PP_ALIGN.CENTER)
    mlb(slide, items, l + Inches(0.15), t + hh + Inches(0.1),
        w - Inches(0.3), h - hh - Inches(0.2), size=size)

def node_box(slide, l, t, w, h, text, fill, tc, bold=True):
    rct(slide, l, t, w, h, fill=fill)
    txb(slide, text, l + Inches(0.15), t + Inches(0.08),
        w - Inches(0.3), h - Inches(0.1),
        size=13, bold=bold, color=tc)

# ─────────────────────────────────
# スライド生成
# ─────────────────────────────────

def make_pptx():
    prs = new_prs()

    # ── Slide 1: タイトル ──────────────────────────────────────────
    s = blank(prs)
    rct(s, 0, 0, W, H, fill=OG)
    rct(s, Inches(1.2), Inches(1.4), W - Inches(2.4), Inches(4.8), fill=WH)
    txb(s, "ST アフェニティチーム",
        Inches(1.5), Inches(1.8), W - Inches(3.0), Inches(0.9),
        size=30, bold=True, color=OG, align=PP_ALIGN.CENTER)
    txb(s, "オンボーディングガイド",
        Inches(1.5), Inches(2.8), W - Inches(3.0), Inches(1.1),
        size=36, bold=True, color=DK, align=PP_ALIGN.CENTER)
    txb(s, "2026年8月  新メンバー向けガイド",
        Inches(1.5), Inches(4.15), W - Inches(3.0), Inches(0.6),
        size=16, color=GY, align=PP_ALIGN.CENTER)

    # ── Slide 2: AGENDA ────────────────────────────────────────────
    s = blank(prs)
    title_bar(s, "AGENDA")
    items = [
        ("①", "ST概要",             "事業モデル・ターゲット・アフェニティの役割"),
        ("②", "KPI体系",            "KPIツリー・タイムラグの理解"),
        ("③", "業務フロー",          "週次・月次ルーティン・承認フロー"),
        ("④", "使用ツール",          "Meta / Canva / ペライチ / Claude Code"),
        ("⑤", "LP・クリエイティブ",  "LP構成・A/Bテスト・訴求軸・命名規則"),
        ("⑥", "分析・KPI報告",       "評価の型・BigQuery・自動報告"),
    ]
    for i, (num, ttl, sub) in enumerate(items):
        top = TH + Inches(0.28) + Inches(i * 0.97)
        rct(s, M, top, Inches(0.65), Inches(0.75), fill=OG)
        txb(s, num, M, top, Inches(0.65), Inches(0.75),
            size=18, bold=True, color=WH, align=PP_ALIGN.CENTER)
        txb(s, ttl,  Inches(1.28), top + Inches(0.07), Inches(3.2), Inches(0.62),
            size=18, bold=True, color=DK)
        txb(s, sub,  Inches(4.6),  top + Inches(0.15), Inches(8.2), Inches(0.5),
            size=13, color=GY)

    # ── Slide 3: ① ST概要 – 事業概要 ──────────────────────────────
    s = blank(prs)
    title_bar(s, "ST概要  ─  事業概要", badge="①")
    boxes = [
        ("塾講師ステーション（ST）とは",
         ["・塾・家庭教師バイト専門の求人サイト",
          "・全国約1.5万件の求人を掲載",
          "・登録・利用はユーザー（大学生）に無料",
          "・スキマ時間でも応募しやすい設計"]),
        ("ビジネスモデル：掲載課金",
         ["・塾側が掲載費を支払うモデル",
          "・ユーザーには一切課金しない",
          "・採用が増えるほど塾の満足度↑→継続利用",
          "∴ 採用数・採用CPAの改善が",
          "　 事業価値の直接的な向上につながる"]),
        ("アフェニティチームの役割",
         ["・Meta広告/Google広告の運用全般",
          "・クリエイティブ・LP・入稿・分析・改善",
          "・週次KPI報告（Claude Codeで自動化）",
          "・目標: LINE登録CPA・応募CPA・採用CPAの最適化"]),
    ]
    bw = Inches(3.9)
    for i, (hdr, its) in enumerate(boxes):
        card(s, M + Inches(i * 4.22), TH + Inches(0.25), bw, Inches(5.85),
             hdr, its, hc=OG, size=12)

    # ── Slide 4: ① KPIフロー ───────────────────────────────────────
    s = blank(prs)
    title_bar(s, "ST概要  ─  アフェニティチームの役割と KPI フロー", badge="①")

    txb(s, "主な業務", M, TH + Inches(0.22), Inches(5.5), Inches(0.45),
        size=14, bold=True, color=OG)
    duties = [
        "・Meta広告・Google広告の運用（クリエイティブ・LP・入稿・分析）",
        "・週次KPI報告の作成（Claude Code /kpi-report で自動化）",
        "・A/Bテスト設計・実施・判定",
        "・クリエイティブ命名・シナリオ設計",
        "・LP改善（FV変更・コピーバリエーション）",
    ]
    mlb(s, duties, M, TH + Inches(0.78), Inches(5.5), Inches(2.8), size=12)

    txb(s, "KPI フロー（上流 → 下流）",
        Inches(6.6), TH + Inches(0.22), Inches(6.4), Inches(0.45),
        size=14, bold=True, color=OG)

    flow = [
        ("IMP（インプレッション数）",  OG,  WH,  True),
        ("↓  CTR（クリック率）",        None, None, False),
        ("LP 流入数",                   OGL, DK,  False),
        ("↓  LP→LINE CVR  ← 主要最適化ポイント ★", None, OG, False),
        ("LINE 登録数  ★  メインKPI",  GN,  WH,  True),
        ("↓  LINE→応募率",              None, None, False),
        ("応募数",                      OGL, DK,  False),
        ("↓  採用率",                   None, None, False),
        ("採用数",                      OGL, DK,  False),
    ]
    ftop = TH + Inches(0.8)
    for label, fill, tc, bold in flow:
        if fill:
            rct(s, Inches(6.6), ftop, Inches(6.3), Inches(0.52), fill=fill)
            txb(s, label, Inches(6.75), ftop + Inches(0.09),
                Inches(6.0), Inches(0.4), size=13, bold=bold, color=tc)
            ftop += Inches(0.56)
        else:
            txb(s, label, Inches(6.85), ftop,
                Inches(6.0), Inches(0.35), size=11, color=tc or GY)
            ftop += Inches(0.37)

    # ── Slide 5: ① 他部署・外部連携 ──────────────────────────────
    s = blank(prs)
    title_bar(s, "ST概要  ─  他部署・外部との連携", badge="①")
    partners = [
        ("営業チーム",
         ["・掲載企業との関係管理・掲載数管理",
          "・採用成果を通じて塾側の満足度を共有",
          "・アフェニティの成果が営業KPIに連動"]),
        ("ペライチ担当",
         ["・LP公開・URL管理・HTML埋め込み対応",
          "・LP改変時は連携して公開タイミングを調整",
          "・FV変更・A/Bテスト開始時は事前連絡必須"]),
        ("外部：Meta 広告審査",
         ["・入稿後に審査が入る。差し戻し時は修正して再入稿",
          "・審査基準は Meta ポリシーに準拠",
          "・薬機法・景品表示法に注意"]),
        ("外部：Canva Pro",
         ["・クリエイティブ制作ツール",
          "・動画・静止画・ストーリーズ制作に使用",
          "・チームフォルダにテンプレートを共有管理"]),
    ]
    pw = Inches(5.9)
    for i, (hdr, its) in enumerate(partners):
        row, col = divmod(i, 2)
        card(s, M + Inches(col * 6.35), TH + Inches(0.25) + Inches(row * 2.9),
             pw, Inches(2.65), hdr, its, hc=OG, hh=Inches(0.55), size=12)

    # ── Slide 6: ① ターゲット3ペルソナ ───────────────────────────
    s = blank(prs)
    title_bar(s, "ST概要  ─  ターゲット 3ペルソナ（大学生 18〜22歳）", badge="①")
    personas = [
        ("タイパ重視（積極探し）", OG,
         ["・すぐ働きたい",
          "・条件（時給・距離）で選ぶ",
          "・登録→即応募が多い"],
         "▶ 訴求軸：ベネフィット型",
         "「30秒で診断・すぐ応募」"),
        ("ミスマッチ回避（単願・慎重）", BL,
         ["・1社に絞って慎重に決めたい",
          "・「本当に合うか」が不安",
          "・口コミ・評判を重視する"],
         "▶ 訴求軸：共感型",
         "「合う塾、見つかる」"),
        ("ミスマッチ回避（併願・比較中）", PU,
         ["・複数社を比較検討中",
          "・差別化ポイントで判断する",
          "・競合も見ている"],
         "▶ 訴求軸：差別化型",
         "「他と比べてみて」"),
    ]
    pw = Inches(3.9)
    for i, (title, color, its, axis, ex) in enumerate(personas):
        l = M + Inches(i * 4.22)
        t = TH + Inches(0.25)
        rct(s, l, t, pw, Inches(5.85), fill=LG)
        rct(s, l, t, pw, Inches(0.62), fill=color)
        txb(s, title, l + Inches(0.1), t + Inches(0.09),
            pw - Inches(0.2), Inches(0.5), size=13, bold=True, color=WH,
            align=PP_ALIGN.CENTER)
        mlb(s, its, l + Inches(0.15), t + Inches(0.75),
            pw - Inches(0.3), Inches(2.3), size=12)
        rct(s, l + Inches(0.1), t + Inches(3.25), pw - Inches(0.2), Inches(2.2),
            fill=WH, line_c=color)
        txb(s, axis, l + Inches(0.2), t + Inches(3.35),
            pw - Inches(0.4), Inches(0.48), size=13, bold=True, color=color)
        txb(s, ex,   l + Inches(0.2), t + Inches(3.95),
            pw - Inches(0.4), Inches(1.2), size=15, bold=True, color=DK,
            align=PP_ALIGN.CENTER)

    # ── Slide 7: ② KPIツリー ───────────────────────────────────────
    s = blank(prs)
    title_bar(s, "KPI体系  ─  KPIツリー（上流 → 下流）", badge="②")

    nodes = [
        ("node",  "IMP（インプレッション数）",             OG,  WH, "配信設定・入札額・ターゲット設定で変化"),
        ("arrow", "↓  CTR（クリック率）",                  None, GY, "クリエイティブの訴求力・コピーの強さ"),
        ("node",  "LP 流入数  ＝  IMP × CTR",              OGL, DK, ""),
        ("arrow", "↓  LP→LINE CVR  ← ★ 主要最適化ポイント", None, OG, "LPのFV・コピー・CTAボタンで大きく変化"),
        ("node",  "LINE 登録数  ★ メインKPI",             GN,  WH, "広告費と CVR の掛け算結果"),
        ("arrow", "↓  LINE→応募率",                        None, GY, "LINEbot の質・診断コンテンツの精度"),
        ("node",  "応募数",                                 OGL, DK, ""),
        ("arrow", "↓  採用率",                              None, GY, "塾の採用プロセス・ミスマッチ度合い"),
        ("node",  "採用数",                                 OGL, DK, ""),
    ]
    ntop = TH + Inches(0.15)
    nh, ah = Inches(0.6), Inches(0.38)
    for typ, label, fill, tc, note in nodes:
        if typ == "node":
            rct(s, M, ntop, Inches(7.0), nh, fill=fill)
            txb(s, label, Inches(0.65), ntop + Inches(0.1),
                Inches(6.6), Inches(0.45), size=14, bold=True, color=tc)
            if note:
                txb(s, f"← {note}", Inches(7.8), ntop + Inches(0.1),
                    Inches(5.0), Inches(0.45), size=11, color=GY)
            ntop += nh + Inches(0.02)
        else:
            txb(s, label, Inches(0.7), ntop,
                Inches(7.0), ah, size=11, color=tc)
            if note:
                txb(s, note, Inches(7.8), ntop,
                    Inches(5.0), ah, size=11, color=GY)
            ntop += ah

    # ── Slide 8: ② 主要KPI定義 ────────────────────────────────────
    s = blank(prs)
    title_bar(s, "KPI体系  ─  主要KPI定義", badge="②")
    hdrs = ["KPI名", "計算式", "意味・目的"]
    rows = [
        ["LINE登録CPA", "広告費 ÷ LINE登録数", "1件のLINE登録を獲得するのにかかったコスト"],
        ["応募CPA",     "広告費 ÷ 応募数",     "1件の応募を獲得するコスト"],
        ["採用CPA（CPF）", "広告費 ÷ 採用数",  "1件の採用（内定承諾）を獲得するコスト"],
        ["LP→LINE CVR", "LINE登録数 ÷ LP流入数 × 100", "LPに来た人のうち何%がLINE登録したか"],
        ["CTR",         "クリック数 ÷ IMP × 100",      "広告を見た人のうち何%がクリックしたか"],
    ]
    add_tbl(s, hdrs, rows, M, TH + Inches(0.3), W - M * 2,
            col_ws=[Inches(2.5), Inches(4.0), Inches(6.2)], rh=Inches(0.6))
    txb(s, "★ 評価基準：spend ≥ 1万円のみ評価対象。それ以下は統計的に不安定なため除外する。",
        M, TH + Inches(4.5), W - M * 2, Inches(0.5), size=12, color=GY)

    # ── Slide 9: ② タイムラグの理解 ──────────────────────────────
    s = blank(prs)
    title_bar(s, "KPI体系  ─  タイムラグの理解（重要）", badge="②")

    txb(s, "なぜ「中央値 40日」のタイムラグがあるの？",
        M, TH + Inches(0.22), Inches(6.8), Inches(0.48),
        size=15, bold=True, color=OG)

    steps = [
        ("LINE 登録（広告経由）",         OG,  WH),
        ("↓  LINEbot 自動返信・診断コンテンツ配信", None, GY),
        ("↓  ユーザーが「本当に応募したい」か検討する期間（ここが長い）", None, GY),
        ("面談申込",                      OGL, DK),
        ("↓  日程調整・面談実施",         None, GY),
        ("採用 / 不採用",                 GN,  WH),
    ]
    stop = TH + Inches(0.82)
    for label, fill, tc in steps:
        if fill:
            rct(s, M, stop, Inches(6.5), Inches(0.52), fill=fill)
            txb(s, label, Inches(0.65), stop + Inches(0.09),
                Inches(6.1), Inches(0.38), size=13, bold=True, color=tc)
            stop += Inches(0.56)
        else:
            txb(s, label, Inches(0.75), stop,
                Inches(6.2), Inches(0.38), size=11, color=tc)
            stop += Inches(0.38)

    # 右：実務ルール
    txb(s, "実務上のルール（必ず守る）",
        Inches(7.5), TH + Inches(0.22), Inches(5.5), Inches(0.48),
        size=15, bold=True, color=OG)
    rules = [
        "【直近40日以内のCV数は「過小評価」として扱う】",
        "　広告効果がまだCVに反映されていない状態。",
        "　少なくても焦らない。",
        "",
        "【評価は「直近90日累計」ベースで行う】",
        "　タイムラグを吸収できる十分な期間。",
        "　週次の数値変動に一喜一憂しない。",
        "",
        "【週次数値は「速度感チェック」のみ】",
        "　異常値（CPAが2倍になった等）の検知に使う。",
        "　週次数値でクリエイティブの優劣を判断しない。",
    ]
    mlb(s, rules, Inches(7.5), TH + Inches(0.82), Inches(5.5), Inches(5.5), size=12)

    # ── Slide 10: ③ 週次ルーティン ────────────────────────────────
    s = blank(prs)
    title_bar(s, "業務フロー  ─  週次ルーティン", badge="③")
    weekly = [
        ("月曜", OG,
         ["・先週KPI集計",
          "・週次報告作成（Claude Code /kpi-report）",
          "・異常値確認（CPA急変・CTR低下等）",
          "・翌週の配信計画確認"]),
        ("火〜木", BL,
         ["・広告運用（クリエイティブ入稿・LP改善）",
          "・BigQueryでクリエイティブ評価・分析",
          "・A/Bテスト進捗確認",
          "・LP改善施策の実施と記録"]),
        ("金曜", GR,
         ["・翌週クリエイティブ準備",
          "・Canva制作・命名規則チェック",
          "・来週の入稿計画確定",
          "・週末の配信状況を最終確認"]),
    ]
    pw = Inches(3.9)
    for i, (day, color, its) in enumerate(weekly):
        card(s, M + Inches(i * 4.22), TH + Inches(0.25), pw, Inches(5.85),
             day, its, hc=color, hh=Inches(0.72), size=12)

    # ── Slide 11: ③ 月次 & 承認フロー ─────────────────────────────
    s = blank(prs)
    title_bar(s, "業務フロー  ─  月次ルーティン & 承認フロー", badge="③")

    txb(s, "月次ルーティン", M, TH + Inches(0.22), Inches(6.2), Inches(0.45),
        size=14, bold=True, color=OG)
    monthly = [
        "【月初】先月の月次KPI報告 → 上長報告",
        "　→ Claude Code /kpi-report（月次モード）で自動生成",
        "",
        "【中旬】A/Bテスト判定",
        "　→ CVR差 +2pt & p<0.05 → 勝ち案を採用",
        "　→ 結果を A/Bテスト計画書SSに必ず記録",
        "",
        "【月末】翌月シナリオ設計",
        "　→ Claude Code /create-scenario を実行",
        "　→ 来月のクリエイティブ方針を決定",
    ]
    mlb(s, monthly, M, TH + Inches(0.82), Inches(6.2), Inches(5.5), size=12)

    txb(s, "承認フロー（必ず守る）",
        Inches(7.2), TH + Inches(0.22), Inches(5.8), Inches(0.45),
        size=14, bold=True, color=OG)
    approvals = [
        ("予算10%超過の変更",
         ["上長確認必須 → 運用管理SSに記録",
          "月間広告費の10%超過は要申請"]),
        ("新クリエイティブ入稿",
         ["命名規則確認 → 入稿",
          "差し戻しリスクは事前にゼロにする"]),
        ("LP改変（FV変更等）",
         ["A/Bテスト計画書に記録してから変更",
          "ペライチ担当に事前連絡必須"]),
    ]
    at = TH + Inches(0.82)
    for aname, adesc in approvals:
        rct(s, Inches(7.2), at, Inches(5.8), Inches(1.55), fill=LG, line_c=OG)
        txb(s, aname, Inches(7.35), at + Inches(0.1),
            Inches(5.4), Inches(0.45), size=13, bold=True, color=OG)
        mlb(s, adesc, Inches(7.35), at + Inches(0.6),
            Inches(5.4), Inches(0.85), size=12)
        at += Inches(1.68)

    # ── Slide 12: ④ ツール一覧 ────────────────────────────────────
    s = blank(prs)
    title_bar(s, "使用ツール  ─  ツール一覧", badge="④")
    hdrs = ["ツール", "主な用途", "ポイント・注意事項"]
    rows = [
        ["Meta 広告管理画面", "広告入稿・キャンペーン設定・配信分析",
         "ABテスト設定もここで。命名規則を確認してから入稿"],
        ["Canva",             "クリエイティブ制作（動画・ストーリーズ）",
         "Pro版。チームフォルダにテンプレートを共有管理"],
        ["ペライチ",          "LP公開・管理（HTML埋め込み対応）",
         "LP変更前にペライチ担当に連絡してから公開"],
        ["Claude Code",       "LP作成・コピー生成・KPI報告 自動化",
         "チャットにスラッシュコマンドを入力するだけ"],
        ["BigQuery",          "広告データ分析・SQLクエリ実行",
         "プロジェクト: bigquery-jukust  OAuth認証（token.json）"],
        ["スプレッドシート（集計さん）", "KPIデータ参照・週次報告",
         "直接編集しない。Claude Codeが自動書き込みする"],
    ]
    add_tbl(s, hdrs, rows, M, TH + Inches(0.28), W - M * 2,
            col_ws=[Inches(2.8), Inches(4.3), Inches(5.5)], rh=Inches(0.56))

    # ── Slide 13: ④ Claude Code スキル ───────────────────────────
    s = blank(prs)
    title_bar(s, "使用ツール  ─  Claude Code スキルの使い方", badge="④")
    txb(s, "Claude Code のチャット欄にスラッシュコマンドを入力するだけ。データ取得→分析→書き込みまで自動で完結します。",
        M, TH + Inches(0.2), W - M * 2, Inches(0.5), size=13, color=DK)

    skills = [
        ("/kpi-report",        "週次・月次KPI報告を自動生成",
         "BigQuery から集計 → スプレッドシート書き込み → 報告文生成。毎週月曜に実行。"),
        ("/lp-create",         "LP新規作成",
         "競合分析 → コピー生成 → HTML生成 → ペライチ向けに整形。"),
        ("/lp-copy-variants",  "FVキャッチコピーのバリエーション生成",
         "ターゲットペルソナに合わせた複数案を出力。A/Bテスト素材の作成に使う。"),
        ("/create-scenario",   "Meta広告のシナリオ設計",
         "訴求軸・動画の型・命名規則に準拠したシナリオを自動生成。月末に実行。"),
    ]
    st = TH + Inches(0.85)
    for cmd, stitle, desc in skills:
        rct(s, M,             st, W - M * 2, Inches(1.3), fill=LG)
        rct(s, M,             st, Inches(2.5), Inches(1.3), fill=DK)
        txb(s, cmd,
            M + Inches(0.1), st + Inches(0.38), Inches(2.3), Inches(0.55),
            size=16, bold=True, color=WH, align=PP_ALIGN.CENTER)
        txb(s, stitle,
            Inches(2.8), st + Inches(0.1), Inches(4.5), Inches(0.45),
            size=14, bold=True, color=OG)
        txb(s, desc,
            Inches(2.8), st + Inches(0.62), W - Inches(3.2), Inches(0.55),
            size=12, color=GY)
        st += Inches(1.42)

    # ── Slide 14: ⑤ LP構成 & ブランドカラー ──────────────────────
    s = blank(prs)
    title_bar(s, "LP・クリエイティブガイド  ─  LP構成 & ブランドカラー", badge="⑤")

    txb(s, "LP構成（上から順番に）",
        M, TH + Inches(0.22), Inches(7.2), Inches(0.45),
        size=14, bold=True, color=OG)
    lp_sects = [
        ("① FV",        "キャッチコピー + CTAボタン（LINE登録）← 最重要。ここで離脱率が決まる"),
        ("② STATS",     "実績数値（1.5万件 / 2.7万人 / 30秒）で信頼感を醸成"),
        ("③ 3ステップ",  "LINE登録 → 診断 → 応募　の流れを可視化"),
        ("④ 口コミ・体験談", "社会的証明。実際のバイト経験者の声"),
        ("⑤ 選ばれる理由", "競合との差別化ポイントを明示"),
        ("⑥ ラストCTA",  "ページ最下部で再度LINE登録を促す"),
    ]
    lt = TH + Inches(0.78)
    for sect, desc in lp_sects:
        rct(s, M, lt, Inches(1.9), Inches(0.62), fill=OG)
        txb(s, sect, M + Inches(0.05), lt + Inches(0.1),
            Inches(1.8), Inches(0.45), size=12, bold=True, color=WH, align=PP_ALIGN.CENTER)
        txb(s, desc, Inches(2.55), lt + Inches(0.1),
            Inches(4.8), Inches(0.45), size=12, color=GY)
        lt += Inches(0.72)

    txb(s, "ブランドカラー",
        Inches(8.2), TH + Inches(0.22), Inches(4.8), Inches(0.45),
        size=14, bold=True, color=OG)
    bcolors = [
        ("#FF7019  メインオレンジ", OG),
        ("#06C755  LINEグリーン（CTAボタン専用）", GN),
        ("#FAE2D1  背景クリーム", CR),
    ]
    bct = TH + Inches(0.82)
    for blabel, bcolor in bcolors:
        rct(s, Inches(8.2), bct, Inches(0.9), Inches(0.62), fill=bcolor,
            line_c=GY if bcolor == CR else None)
        txb(s, blabel, Inches(9.25), bct + Inches(0.12),
            Inches(3.7), Inches(0.42), size=12, color=DK)
        bct += Inches(0.82)
    txb(s, "★ FVのCTAボタンは必ずLINEグリーン（#06C755）を使用すること",
        Inches(8.2), TH + Inches(3.35), Inches(4.8), Inches(0.5),
        size=12, bold=True, color=OG)

    # ── Slide 15: ⑤ A/Bテスト ─────────────────────────────────────
    s = blank(prs)
    title_bar(s, "LP・クリエイティブガイド  ─  A/Bテストの進め方", badge="⑤")

    txb(s, "進め方", M, TH + Inches(0.22), Inches(6.5), Inches(0.45),
        size=14, bold=True, color=OG)
    ab_steps = [
        "① 指標を決める：LP→LINE CVR をメインとする",
        "② 同一クリエイティブで LP-A と LP-B を同時配信",
        "③ 配信期間：最低2週間 / spend ≥ ¥50,000 が目安",
        "④ 判定：CVR差 +2pt 以上 & p<0.05 → 勝ち案を採用",
        "⑤ 結果を A/Bテスト計画書SSに必ず記録する",
    ]
    mlb(s, ab_steps, M, TH + Inches(0.82), Inches(6.5), Inches(3.5), size=13)

    rct(s, Inches(7.2), TH + Inches(0.22), Inches(5.8), Inches(5.9), fill=LG, line_c=OG)
    txb(s, "「p<0.05」ってどういう意味？",
        Inches(7.35), TH + Inches(0.32), Inches(5.5), Inches(0.45),
        size=14, bold=True, color=OG)
    p_ex = [
        "「この差は偶然ではなく、",
        "本当の差である確率が 95% 以上」",
        "",
        "実務での判断の目安：",
        "・spend ≥ ¥50,000 を超えてから判定する",
        "・CV数 ≥ 30件 が揃ってから判定する",
        "・2週間は必ず続ける（途中判断しない）",
        "",
        "★ 数値が揃うまでは「参考値」として扱い",
        "　 配信継続を優先する",
    ]
    mlb(s, p_ex, Inches(7.35), TH + Inches(0.92), Inches(5.5), Inches(5.0), size=12)

    # ── Slide 16: ⑤ 5訴求軸 ───────────────────────────────────────
    s = blank(prs)
    title_bar(s, "LP・クリエイティブガイド  ─  5つの訴求軸", badge="⑤")
    hdrs = ["訴求軸", "コンセプト", "コピー例", "刺さるターゲット"]
    rows = [
        ["課題解決型",   "ペインを言語化",     "「合う塾が見つからない?」", "ミスマッチ回避層"],
        ["ベネフィット型", "得られる未来を提示", "「収入UP・就活ガクチカになる」", "タイパ重視層"],
        ["数字型",       "実績・信頼数字を強調", "「1.5万件・2.7万人・30秒」", "慎重派・比較型"],
        ["共感型",       "感情に寄り添う",     "「その気持ち、わかる」",  "単願ミスマッチ回避"],
        ["差別化型",     "競合との違いを明示",  "「他のバイトと違う理由」", "併願・比較型"],
    ]
    add_tbl(s, hdrs, rows, M, TH + Inches(0.28), W - M * 2,
            col_ws=[Inches(2.2), Inches(3.0), Inches(3.9), Inches(3.5)], rh=Inches(0.58))
    txb(s, "※ 訴求軸はターゲットペルソナに合わせて選ぶ。1広告=1訴求軸を徹底すること。",
        M, TH + Inches(5.35), W - M * 2, Inches(0.5), size=12, color=GY)

    # ── Slide 17: ⑤ シナリオ設計 & 命名規則 ──────────────────────
    s = blank(prs)
    title_bar(s, "LP・クリエイティブガイド  ─  シナリオ設計 & 命名規則", badge="⑤")

    txb(s, "動画広告シナリオの型",
        M, TH + Inches(0.22), Inches(6.2), Inches(0.45),
        size=14, bold=True, color=OG)
    sc_parts = [
        ("フック（0〜3秒）",    "共感・問いかけでスクロールを止める",
         "例: 「塾講師バイト、何社見ても決まらない…」"),
        ("ボディ（3〜15秒）",   "問題提起 → ST が解決 → 実績で信頼獲得",
         "例: 「STなら30秒で自分に合う塾を診断できる」"),
        ("CTA（ラスト3秒）",    "明確な行動を促す",
         "「LINE登録して」or「適職診断してみて」"),
    ]
    sct = TH + Inches(0.82)
    for part, desc, ex in sc_parts:
        rct(s, M, sct, Inches(6.2), Inches(1.58), fill=LG, line_c=OG)
        txb(s, part,  M + Inches(0.15), sct + Inches(0.1),
            Inches(5.9), Inches(0.45), size=13, bold=True, color=OG)
        txb(s, desc,  M + Inches(0.15), sct + Inches(0.58),
            Inches(5.9), Inches(0.4), size=12, color=DK)
        txb(s, ex,    M + Inches(0.15), sct + Inches(1.05),
            Inches(5.9), Inches(0.42), size=11, color=GY)
        sct += Inches(1.68)

    txb(s, "命名規則（必ず準拠）",
        Inches(7.2), TH + Inches(0.22), Inches(5.8), Inches(0.45),
        size=14, bold=True, color=OG)
    rct(s, Inches(7.2), TH + Inches(0.82), Inches(5.8), Inches(0.65), fill=DK)
    txb(s, "形式: [訴求軸]_[動画の型]_[詳細]_[日付]",
        Inches(7.35), TH + Inches(0.93), Inches(5.5), Inches(0.48),
        size=13, bold=True, color=WH)

    examples = [
        ("BN_TS_塾バイトデビュー_250801",    "ベネフィット型・テスティモニアル"),
        ("KD_PB_合う塾が見つからない_250808", "課題解決型・問題提起"),
        ("DZ_CC_他のバイトと違う理由_250815", "差別化型・比較型"),
    ]
    et = TH + Inches(1.6)
    for ename, edesc in examples:
        rct(s, Inches(7.2), et, Inches(5.8), Inches(0.88), fill=LG)
        txb(s, ename, Inches(7.35), et + Inches(0.06),
            Inches(5.5), Inches(0.42), size=12, bold=True, color=OG)
        txb(s, f"→ {edesc}", Inches(7.35), et + Inches(0.48),
            Inches(5.5), Inches(0.34), size=11, color=GY)
        et += Inches(0.96)
    txb(s, "★ 詳細は knowledge/creative/meta-ads-naming.md を必ず確認",
        Inches(7.2), et + Inches(0.05), Inches(5.8), Inches(0.45),
        size=12, bold=True, color=OG)

    # ── Slide 18: ⑥ 分析の型 ─────────────────────────────────────
    s = blank(prs)
    title_bar(s, "分析・KPI報告  ─  分析の型とクリエイティブ評価", badge="⑥")

    txb(s, "分析のアウトプット形式（この順序を必ず守る）",
        M, TH + Inches(0.22), Inches(6.5), Inches(0.45),
        size=14, bold=True, color=OG)
    a_steps = [
        ("① 結論",      "1〜2行で即答する\n例: 「○○クリエイティブのCPAが最良（¥18,920）」"),
        ("② 根拠データ", "表形式で：ad_name / spend / purchase / CPA を並べる"),
        ("③ 推奨アクション", "優先度付きで3件以内に絞る"),
    ]
    at2 = TH + Inches(0.82)
    for step, desc in a_steps:
        rct(s, M,            at2, Inches(0.85), Inches(1.28), fill=OG)
        txb(s, step, M + Inches(0.05), at2 + Inches(0.35),
            Inches(0.75), Inches(0.6), size=12, bold=True, color=WH, align=PP_ALIGN.CENTER)
        rct(s, Inches(1.15), at2, Inches(5.5), Inches(1.28), fill=LG)
        mlb(s, desc.split('\n'), Inches(1.3), at2 + Inches(0.18),
            Inches(5.2), Inches(1.0), size=12)
        at2 += Inches(1.42)

    txb(s, "クリエイティブ評価の手順",
        Inches(7.5), TH + Inches(0.22), Inches(5.5), Inches(0.45),
        size=14, bold=True, color=OG)
    eval_items = [
        "① 評価期間：直近90日累計（週次は速度感チェックのみ）",
        "② 評価指標：CPA = SAFE_DIVIDE(spend, purchase)",
        "③ 対象：spend ≥ 1万円のみ（小額は除外）",
        "④ 命名規則で訴求軸・動画の型を分類しパターン分析",
        "⑤ 結論→根拠→アクションの形式でまとめる",
    ]
    mlb(s, eval_items, Inches(7.5), TH + Inches(0.82), Inches(5.5), Inches(3.2), size=12)

    txb(s, "証拠強度の表記ルール",
        Inches(7.5), TH + Inches(4.15), Inches(5.5), Inches(0.42),
        size=13, bold=True, color=OG)
    ev_items = [
        "★★★  BigQueryのデータで直接示せる → そのまま断言",
        "★★　  複数データが一致 → 「〜と推測される」と表記",
        "★　　  論理的推測のみ → 「推定: 〜」と必ず明記",
    ]
    mlb(s, ev_items, Inches(7.5), TH + Inches(4.7), Inches(5.5), Inches(1.4), size=12)

    # ── Slide 19: ⑥ BigQuery & 週次KPI報告 ──────────────────────
    s = blank(prs)
    title_bar(s, "分析・KPI報告  ─  BigQuery & 週次KPI報告", badge="⑥")

    txb(s, "BigQuery 接続情報",
        M, TH + Inches(0.22), Inches(6.2), Inches(0.45),
        size=14, bold=True, color=OG)
    bq_rows = [
        ["プロジェクト", "bigquery-jukust"],
        ["認証方式",     "OAuth（token.json）※サービスアカウント禁止"],
        ["主要ビュー（ST）",  "ST_meta_rpt.v_ST_meta_campaign_report"],
        ["主要ビュー（CA）",  "CA_meta_rpt.v_CA_meta_ads_daily_report_with_scenario"],
        ["クエリパターン",    "必ずCTEパターン使用（ビューに直接GROUP BYしない）"],
    ]
    add_tbl(s, ["項目", "値"], bq_rows, M, TH + Inches(0.8), Inches(6.2),
            col_ws=[Inches(1.9), Inches(4.1)], rh=Inches(0.58))

    txb(s, "週次KPI報告の自動化フロー",
        Inches(7.3), TH + Inches(0.22), Inches(5.7), Inches(0.45),
        size=14, bold=True, color=OG)
    rf = [
        ("Claude Code で「/kpi-report」と入力", OG, WH),
        ("↓", None, None),
        ("BigQuery から自動クエリ実行", LG, DK),
        ("↓", None, None),
        ("スプレッドシート（集計さん）に自動書き込み", LG, DK),
        ("↓", None, None),
        ("報告文・分析コメントを生成", LG, DK),
        ("↓", None, None),
        ("内容を確認して上長に共有", GN, WH),
    ]
    rft = TH + Inches(0.82)
    for label, fill, tc in rf:
        if fill:
            rct(s, Inches(7.3), rft, Inches(5.7), Inches(0.52), fill=fill)
            txb(s, label, Inches(7.45), rft + Inches(0.09),
                Inches(5.4), Inches(0.38), size=13, bold=(fill == OG or fill == GN),
                color=tc)
            rft += Inches(0.56)
        else:
            txb(s, label, Inches(7.3), rft, Inches(5.7), Inches(0.32),
                size=14, color=GY, align=PP_ALIGN.CENTER)
            rft += Inches(0.32)

    # ── Slide 20: チェックリスト ──────────────────────────────────
    s = blank(prs)
    title_bar(s, "チェックリスト  ─  習熟度の目安")
    levels = [
        ("理解レベル\n（まず身につける）", OG,
         ["□ ST事業・掲載課金モデルを説明できる",
          "□ 3ペルソナの違いと訴求軸を言える",
          "□ KPIツリー（IMP→採用）を把握している",
          "□ タイムラグ（中央値40日・90日評価）\n　 を理解している"]),
        ("基礎レベル\n（1週間以内）", BL,
         ["□ 各ツールにログイン・基本操作できる",
          "□ 命名規則マスタを読んだ",
          "□ /kpi-report で週次報告を1回作成した",
          "□ 既存LPのFVキャッチコピーを把握した"]),
        ("応用レベル\n（1ヶ月以内）", GR,
         ["□ A/Bテストを設計・実行・判定できる",
          "□ BigQueryでクリエイティブ評価クエリを\n　 書ける",
          "□ Claude Codeスキルを自力で使いこなせる",
          "□ 週次報告を上長に提出できる"]),
    ]
    pw = Inches(3.9)
    for i, (title, color, its) in enumerate(levels):
        card(s, M + Inches(i * 4.22), TH + Inches(0.25), pw, Inches(5.85),
             title, its, hc=color, hh=Inches(0.8), size=12)

    # ── Slide 21: まとめ ───────────────────────────────────────────
    s = blank(prs)
    rct(s, 0, 0, W, H, fill=OG)
    rct(s, Inches(1.0), Inches(1.4), W - Inches(2.0), Inches(4.8), fill=WH)
    txb(s, "KPIを理解して、クリエイティブとLPで",
        Inches(1.5), Inches(1.9), W - Inches(3.0), Inches(0.9),
        size=26, bold=True, color=DK, align=PP_ALIGN.CENTER)
    txb(s, "CVR を上げていく仕事",
        Inches(1.5), Inches(2.9), W - Inches(3.0), Inches(1.0),
        size=34, bold=True, color=OG, align=PP_ALIGN.CENTER)
    txb(s, "わからないことは Claude Code に聞いて。スキルと knowledge が助けてくれる。",
        Inches(1.5), Inches(4.1), W - Inches(3.0), Inches(0.65),
        size=15, color=GY, align=PP_ALIGN.CENTER)
    txb(s, "SS版: 1UakK5ig5spCTQmgdrd32XsJjiHLyAmGhymb1B5o-i8s  |  BigQuery: bigquery-jukust",
        Inches(1.5), Inches(5.1), W - Inches(3.0), Inches(0.45),
        size=11, color=GY, align=PP_ALIGN.CENTER)

    return prs


# ─────────────────────────────────
# メイン実行
# ─────────────────────────────────
if __name__ == "__main__":
    print("PPTX生成中...")
    prs = make_pptx()
    output = "scripts/data/onboarding_affinity_2026.pptx"
    prs.save(output)
    print(f"保存完了: {output}")
    print(f"スライド数: {len(prs.slides)} 枚")
