#!/usr/bin/env python3
# coding: utf-8
"""ST Meta広告 運用引き継ぎ資料 PowerPoint生成"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

OUTPUT = "/Users/119322/Desktop/claude-code-template_af/scripts/data/handover_st_meta.pptx"

# ── カラーパレット ──────────────────────────────────────────
C_DARK_BLUE   = RGBColor(0x1A, 0x3A, 0x5C)   # タイトル背景
C_MID_BLUE    = RGBColor(0x22, 0x5E, 0xA8)   # セクションヘッダー
C_LIGHT_BLUE  = RGBColor(0xD6, 0xE4, 0xF7)   # テーブルヘッダー背景
C_ACCENT      = RGBColor(0xE8, 0x6A, 0x2E)   # 強調（オレンジ）
C_WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK       = RGBColor(0x1A, 0x1A, 0x1A)
C_GREY        = RGBColor(0x9E, 0x9E, 0x9E)
C_LIGHT_GREY  = RGBColor(0xF5, 0xF5, 0xF5)
C_GREEN       = RGBColor(0x27, 0xAE, 0x60)
C_RED         = RGBColor(0xC0, 0x39, 0x2B)
C_YELLOW_BG   = RGBColor(0xFF, 0xF3, 0xCD)

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)

BLANK = prs.slide_layouts[6]  # 完全ブランク

# ── ヘルパー ───────────────────────────────────────────────
def add_rect(slide, l, t, w, h, fill_color=None, line_color=None, line_width=None):
    shape = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
        if line_width:
            shape.line.width = Pt(line_width)
    else:
        shape.line.fill.background()
    return shape

def add_text(slide, text, l, t, w, h,
             font_size=18, bold=False, color=C_BLACK,
             align=PP_ALIGN.LEFT, wrap=True, italic=False):
    txBox = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txBox.word_wrap = wrap
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox

def add_label(slide, text, l, t, w, h, bg_color, text_color=C_WHITE, font_size=11, bold=True):
    add_rect(slide, l, t, w, h, fill_color=bg_color)
    add_text(slide, text, l+0.05, t+0.02, w-0.1, h-0.04,
             font_size=font_size, bold=bold, color=text_color, align=PP_ALIGN.CENTER)

def add_slide_header(slide, title, subtitle=None):
    """各スライド共通のトップバー"""
    add_rect(slide, 0, 0, 13.33, 1.0, fill_color=C_MID_BLUE)
    add_text(slide, title, 0.4, 0.08, 12, 0.55,
             font_size=24, bold=True, color=C_WHITE)
    if subtitle:
        add_text(slide, subtitle, 0.4, 0.62, 12, 0.35,
                 font_size=12, color=RGBColor(0xBB, 0xD6, 0xF5))
    # 右上に資料名
    add_text(slide, "ST Meta広告 運用引き継ぎ資料", 9.5, 0.72, 3.7, 0.28,
             font_size=9, color=RGBColor(0xBB, 0xD6, 0xF5), align=PP_ALIGN.RIGHT)

def add_table(slide, l, t, w, headers, rows, header_bg=C_LIGHT_BLUE, row_height=0.4):
    """シンプルなテーブル"""
    col_w = w / len(headers)
    y = t
    # ヘッダー行
    for ci, h in enumerate(headers):
        add_rect(slide, l + ci*col_w, y, col_w, row_height, fill_color=header_bg,
                 line_color=C_MID_BLUE, line_width=0.5)
        add_text(slide, h, l + ci*col_w + 0.05, y + 0.05, col_w - 0.1, row_height - 0.1,
                 font_size=11, bold=True, color=C_DARK_BLUE)
    y += row_height
    for ri, row in enumerate(rows):
        row_bg = C_WHITE if ri % 2 == 0 else C_LIGHT_GREY
        for ci, cell in enumerate(row):
            add_rect(slide, l + ci*col_w, y, col_w, row_height, fill_color=row_bg,
                     line_color=RGBColor(0xCC, 0xCC, 0xCC), line_width=0.3)
            add_text(slide, str(cell), l + ci*col_w + 0.05, y + 0.04, col_w - 0.1, row_height - 0.08,
                     font_size=10, color=C_BLACK)
        y += row_height

def add_bullet_box(slide, l, t, w, h, bullets, title=None, title_color=C_MID_BLUE, font_size=12):
    """箇条書きボックス"""
    if title:
        add_text(slide, title, l, t, w, 0.35,
                 font_size=13, bold=True, color=title_color)
        t += 0.38
        h -= 0.38
    txBox = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txBox.word_wrap = True
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = bullet
        run.font.size = Pt(font_size)
        run.font.color.rgb = C_BLACK

# ═══════════════════════════════════════════════════════════
# SLIDE 1: タイトルスライド
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, 13.33, 7.5, fill_color=C_DARK_BLUE)
# ロゴ的な装飾
add_rect(s, 0, 5.5, 13.33, 2.0, fill_color=RGBColor(0x12, 0x2A, 0x45))
add_rect(s, 0.5, 2.6, 0.08, 2.2, fill_color=C_ACCENT)

add_text(s, "ST Meta広告", 0.8, 1.6, 11, 1.2,
         font_size=48, bold=True, color=C_WHITE)
add_text(s, "運用引き継ぎ資料", 0.8, 2.7, 11, 1.0,
         font_size=42, bold=True, color=RGBColor(0xBB, 0xD6, 0xF5))
add_text(s, "引き継ぎ元: 丸山大輝　→　引き継ぎ先: 足立清美", 0.8, 4.0, 11, 0.5,
         font_size=16, color=C_GREY)
add_text(s, "作成日: 2026年8月", 0.8, 4.5, 11, 0.4,
         font_size=14, color=C_GREY)

# ═══════════════════════════════════════════════════════════
# SLIDE 2: AGENDA
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "AGENDA")
add_rect(s, 0, 1.0, 13.33, 6.5, fill_color=C_LIGHT_GREY)

items = [
    ("①", "ST概要",         "事業モデル・ターゲット・アフェニティチームの役割"),
    ("②", "KPI体系",        "KPIツリー・タイムラグの理解・評価サイクル"),
    ("③", "データ計測環境",  "BigQuery・管理画面・既知の問題点（CV計測の注意）"),
    ("④", "業務フロー",      "週次・月次ルーティン・クリエイティブ制作フロー"),
    ("⑤", "使用ツール",      "Meta / Canva / ペライチ / Claude Code スキル"),
    ("⑥", "引き継ぎ時点の状況", "B2キャンペーン停止経緯・現在の課題・推奨アクション"),
    ("⑦", "参考リンク集",    "スプシ・Google Doc・BigQuery・Claude Codeスキル一覧"),
]
for i, (num, title, desc) in enumerate(items):
    y = 1.3 + i * 0.73
    add_rect(s, 0.6, y, 0.55, 0.5, fill_color=C_MID_BLUE)
    add_text(s, num, 0.6, y + 0.05, 0.55, 0.42,
             font_size=16, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text(s, title, 1.3, y + 0.02, 2.5, 0.26,
             font_size=15, bold=True, color=C_DARK_BLUE)
    add_text(s, desc, 1.3, y + 0.25, 10.5, 0.25,
             font_size=11, color=C_GREY)

# ═══════════════════════════════════════════════════════════
# SLIDE 3: ST概要
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "① ST概要", "事業モデル・ターゲット・アフェニティチームのミッション")

# 左: 事業概要
add_rect(s, 0.3, 1.15, 5.9, 5.9, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "事業概要", 0.3, 1.15, 5.9, 0.38, C_MID_BLUE)

info = [
    ("サービス", "塾講師ステーション（ST）"),
    ("業種", "塾・家庭教師バイト専門 求人サイト"),
    ("モデル", "掲載課金（塾側が掲載費を支払う。ユーザー無料）"),
    ("ターゲット", "18〜22歳 大学生（潜在層）"),
    ("強み", "15万件以上の口コミ・塾ブランド診断コンテンツ"),
]
for i, (k, v) in enumerate(info):
    y = 1.65 + i * 0.67
    add_text(s, k, 0.5, y, 1.1, 0.35, font_size=10, bold=True, color=C_MID_BLUE)
    add_text(s, v, 1.65, y, 4.3, 0.35, font_size=11, color=C_BLACK)
    if i < len(info)-1:
        add_rect(s, 0.5, y + 0.42, 5.5, 0.01, fill_color=RGBColor(0xE0,0xE0,0xE0))

# 右: ターゲット3ペルソナ
add_rect(s, 6.5, 1.15, 6.5, 5.9, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "ターゲット 3ペルソナ（大学生 18〜22歳）", 6.5, 1.15, 6.5, 0.38, C_MID_BLUE)

personas = [
    ("タイパ重視層",      "すぐ働きたい。条件（時給・距離）で選ぶ積極探し層",   "効率・コスパ・すぐ見つかる",   C_MID_BLUE),
    ("ミスマッチ回避・単願型", "ブラックが怖い。自分に教えられるか不安。慎重派",    "口コミ・安心感・実態がわかる",  RGBColor(0x27,0x80,0x5E)),
    ("ミスマッチ回避・併願型", "飲食と塾どっちが合うか分からない。比較して選びたい", "比較・差別化・塾ならでは",     RGBColor(0x8E, 0x44, 0xAD)),
]
for i, (name, desc, appeal, color) in enumerate(personas):
    y = 1.65 + i * 1.7
    add_rect(s, 6.65, y, 6.2, 1.5, fill_color=C_LIGHT_GREY)
    add_rect(s, 6.65, y, 0.12, 1.5, fill_color=color)
    add_text(s, name, 6.9, y + 0.05, 5.8, 0.35, font_size=13, bold=True, color=color)
    add_text(s, desc, 6.9, y + 0.42, 5.8, 0.45, font_size=10, color=C_BLACK)
    add_text(s, f"刺さる訴求: {appeal}", 6.9, y + 0.95, 5.8, 0.35,
             font_size=10, bold=True, color=C_MID_BLUE)

# アフェニティミッション
add_rect(s, 0.3, 6.75, 12.7, 0.55, fill_color=RGBColor(0xFF, 0xF3, 0xCD))
add_text(s, "アフェニティのミッション: Meta広告でSNS潜在層を獲得し、LINE登録→応募につなげること",
         0.5, 6.8, 12.3, 0.45, font_size=12, bold=True, color=RGBColor(0x7D, 0x60, 0x08))

# ═══════════════════════════════════════════════════════════
# SLIDE 4: KPI体系
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "② KPI体系", "ファネル構造・タイムラグの理解・評価サイクル")

# ファネル（左側）
add_rect(s, 0.3, 1.15, 5.8, 5.9, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "広告〜応募 ファネル", 0.3, 1.15, 5.8, 0.38, C_MID_BLUE)

funnel = [
    ("IMP（インプレッション）", "Meta広告表示", C_LIGHT_BLUE),
    ("CTR（クリック率）",        "広告クリック",  RGBColor(0xC5, 0xD9, 0xF1)),
    ("LP流入",                  "LPビュー数",   RGBColor(0xA9, 0xCC, 0xE3)),
    ("CVR / CPF",               "LINE登録",     RGBColor(0x8A, 0xBD, 0xD6)),
    ("応募数 / 応募CPA",        "応募 ← 最重要KPI", RGBColor(0x22, 0x5E, 0xA8)),
]
for i, (kpi, label, color) in enumerate(funnel):
    y = 1.65 + i * 0.95
    w = 5.0 - i * 0.3
    x = 0.65 + i * 0.15
    add_rect(s, x, y, w, 0.7, fill_color=color)
    add_text(s, kpi, x + 0.1, y + 0.05, w - 0.2, 0.3,
             font_size=12, bold=(i == 4), color=C_WHITE if i >= 3 else C_DARK_BLUE)
    add_text(s, label, x + 0.1, y + 0.35, w - 0.2, 0.28,
             font_size=10, color=C_WHITE if i >= 3 else C_GREY)

# 右側: タイムラグ + 評価サイクル
add_rect(s, 6.4, 1.15, 6.6, 2.8, fill_color=RGBColor(0xFF, 0xEC, 0xEC),
         line_color=C_RED, line_width=0.5)
add_label(s, "⚠ タイムラグ（最重要・必ず理解する）", 6.4, 1.15, 6.6, 0.38,
          RGBColor(0xC0, 0x39, 0x2B))
lag_items = [
    "Meta FV登録 → 応募まで 中央値 40日",
    "",
    "意味: 直近40日以内のCV数は「過小評価」",
    "　→ 足元のCPAを見て慌てない",
    "",
    "評価方法: 直近90日累計で判断",
    "週次の数字は速度感チェックのみ",
]
for i, t in enumerate(lag_items):
    add_text(s, t, 6.6, 1.63 + i * 0.3, 6.2, 0.28,
             font_size=11, bold=(i == 0), color=C_RED if i == 0 else C_BLACK)

add_rect(s, 6.4, 4.15, 6.6, 2.9, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "KPI評価サイクル", 6.4, 4.15, 6.6, 0.38, C_MID_BLUE)
add_table(s, 6.5, 4.65, 6.3,
          ["頻度", "確認内容", "重みづけ"],
          [
              ["週次", "LINE登録数・CPFの速度感", "参考のみ"],
              ["月次", "直近90日累計 応募CPA", "本評価"],
              ["四半期", "予算配分・チャネル戦略見直し", "意思決定"],
          ],
          row_height=0.62)

# CPF目安
add_rect(s, 6.4, 7.1, 6.6, 0.35, fill_color=RGBColor(0xD5, 0xE8, 0xD4))
add_text(s, "CPF目安: ¥1,500〜3,000 / LINE登録1件", 6.6, 7.14, 6.3, 0.28,
         font_size=11, bold=True, color=RGBColor(0x27, 0x6A, 0x27))

# ═══════════════════════════════════════════════════════════
# SLIDE 5: データ計測環境（BQ・管理画面）
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "③ データ計測環境", "BigQuery・管理画面・既知の問題点")

# 左: BQ環境
add_rect(s, 0.3, 1.15, 6.0, 3.3, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "BigQuery 環境", 0.3, 1.15, 6.0, 0.38, C_MID_BLUE)
bq_items = [
    ("プロジェクトID",  "bigquery-jukust"),
    ("主要ビュー",     "ST_meta_rpt.v_ST_meta_campaign_report"),
    ("認証方法",       "OAuth（token.json）・サービスアカウント禁止"),
    ("分析ツール",     "Claude Code（BQ自動クエリ対応）"),
    ("スキル",         "kpi-reportスキル で週次KPI自動取得"),
]
for i, (k, v) in enumerate(bq_items):
    y = 1.65 + i * 0.5
    add_text(s, k, 0.5, y, 1.5, 0.3, font_size=10, bold=True, color=C_MID_BLUE)
    add_text(s, v, 2.1, y, 4.0, 0.3, font_size=10, color=C_BLACK)

# 右: 管理画面
add_rect(s, 6.6, 1.15, 6.4, 3.3, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "Meta広告管理画面", 6.6, 1.15, 6.4, 0.38, C_MID_BLUE)
mgmt_items = [
    ("URL",    "business.facebook.com"),
    ("用途",   "広告入稿・予算管理・CVコンバージョン確認"),
    ("注意点", "標準表示はクリック後7日間のみカウント"),
    ("推奨",   "アトリビューション: 28日クリック+1日視聴に変更"),
    ("連携",   "Meta Data Transfer → BigQueryに自動同期"),
]
for i, (k, v) in enumerate(mgmt_items):
    y = 1.65 + i * 0.5
    add_text(s, k, 6.8, y, 1.2, 0.3, font_size=10, bold=True, color=C_MID_BLUE)
    add_text(s, v, 8.05, y, 4.8, 0.3, font_size=10, color=C_BLACK)

# 既知の問題点（重要）
add_rect(s, 0.3, 4.6, 12.7, 2.7, fill_color=RGBColor(0xFF, 0xEC, 0xEC),
         line_color=C_RED, line_width=0.8)
add_label(s, "⚠ 既知の問題点（引き継ぎ時点で未解決）", 0.3, 4.6, 12.7, 0.4,
          RGBColor(0xC0, 0x39, 0x2B))

problems = [
    (
        "問題①: BQ vs 管理画面のCV数値乖離",
        [
            "BQパイプラインはビュースルーCV（動画視聴後1日以内）を含めてカウント",
            "管理画面のデフォルトはクリック後7日間のみ → 数字が食い違う",
            "対応: 管理画面のアトリビューション設定を変更して一致させる",
        ]
    ),
    (
        "問題②: custom_cv_2（応募CV）バグ",
        [
            "BQビューの custom_cv_2 が complete_registration（LINE登録CV）と同じ値を返す",
            "原因: Meta側のカスタムコンバージョン設定不備（要確認・修正）",
            "現状対処: 応募CVは「ST_Meta集計さん」への手動記入でフォールバック",
        ]
    ),
]
for ci, (title, bullets) in enumerate(problems):
    x = 0.5 + ci * 6.4
    add_text(s, title, x, 5.1, 6.0, 0.3, font_size=11, bold=True, color=C_RED)
    for bi, b in enumerate(bullets):
        add_text(s, f"・ {b}", x, 5.45 + bi * 0.38, 6.1, 0.35, font_size=10, color=C_BLACK)

# ═══════════════════════════════════════════════════════════
# SLIDE 6: 業務フロー
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "④ 業務フロー", "週次・月次ルーティン・クリエイティブ制作フロー")

# 週次
add_rect(s, 0.3, 1.15, 6.0, 3.0, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "週次ルーティン", 0.3, 1.15, 6.0, 0.38, C_MID_BLUE)
weekly = [
    ("月曜", "KPI確認（LINE登録数・CPF速度感チェック）"),
    ("月曜", "週次KPI報告作成（Claude Code /kpi-report）"),
    ("火〜木", "広告運用（入稿・予算調整・クリエイティブ評価）"),
    ("金曜", "翌週クリエイティブ準備・Canva制作・命名規則チェック"),
]
for i, (day, task) in enumerate(weekly):
    y = 1.63 + i * 0.55
    add_label(s, day, 0.5, y, 1.0, 0.38, C_LIGHT_BLUE, text_color=C_DARK_BLUE, font_size=10)
    add_text(s, task, 1.65, y + 0.04, 4.5, 0.38, font_size=11, color=C_BLACK)

# 月次
add_rect(s, 6.5, 1.15, 6.5, 3.0, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "月次ルーティン", 6.5, 1.15, 6.5, 0.38, C_MID_BLUE)
monthly = [
    ("月初", "前月の直近90日累計KPI集計・クリエイティブ評価"),
    ("月初", "予算配分の確認・翌月計画"),
    ("月中", "A/Bテスト中間確認（各案500UU以上か）"),
    ("月末", "A/Bテスト判定・勝ち案展開"),
    ("通年", "月別季節変数に基づく訴求軸・シナリオ見直し"),
]
for i, (timing, task) in enumerate(monthly):
    y = 1.63 + i * 0.48
    add_label(s, timing, 6.7, y, 0.9, 0.38, C_LIGHT_BLUE, text_color=C_DARK_BLUE, font_size=10)
    add_text(s, task, 7.7, y + 0.04, 5.1, 0.38, font_size=10, color=C_BLACK)

# クリエイティブ制作フロー
add_rect(s, 0.3, 4.3, 12.7, 3.0, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "クリエイティブ制作フロー", 0.3, 4.3, 12.7, 0.38, C_MID_BLUE)
steps = [
    ("STEP 1", "月別季節変数・訴求軸確認"),
    ("STEP 2", "シナリオ作成（create-scenarioスキル）"),
    ("STEP 3", "Canvaで動画/デザイン制作"),
    ("STEP 4", "LPとの訴求整合性チェック"),
    ("STEP 5", "Meta広告管理画面に入稿・命名"),
    ("STEP 6", "配信24h後にCTR確認"),
]
for i, (step, desc) in enumerate(steps):
    x = 0.5 + i * 2.1
    add_rect(s, x, 4.8, 1.9, 0.38, fill_color=C_MID_BLUE)
    add_text(s, step, x, 4.82, 1.9, 0.34,
             font_size=10, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text(s, desc, x, 5.28, 1.9, 0.7, font_size=10, color=C_BLACK)
    if i < 5:
        add_text(s, "→", x + 1.92, 4.88, 0.25, 0.28,
                 font_size=14, bold=True, color=C_MID_BLUE)

add_text(s, "LP改善フロー: 既存LP CVR確認 → コピーバリエーション生成（lp-copy-variants）→ Canvaデザイン → ペライチ実装 → A/B配信 → 2週間後判定",
         0.5, 6.1, 12.3, 0.45, font_size=10, color=C_GREY)
add_text(s, "A/Bテスト最低基準: 各案 500UU以上 かつ spend 3万円以上でCVR差が明確に出てから判定すること",
         0.5, 6.6, 12.3, 0.45, font_size=10, bold=True, color=RGBColor(0xC0, 0x39, 0x2B))

# ═══════════════════════════════════════════════════════════
# SLIDE 7: 使用ツール & Claude Codeスキル
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "⑤ 使用ツール", "Meta / Canva / ペライチ / Claude Code スキル一覧")

add_table(s, 0.3, 1.2, 12.7,
          ["ツール名", "用途・役割", "アクセス方法", "習熟優先度"],
          [
              ["Meta広告管理画面", "広告入稿・予算管理・パフォーマンス確認", "business.facebook.com", "★★★"],
              ["Canva", "動画・画像クリエイティブ制作（Storiesデザイン）", "canva.com / チームアカウント", "★★★"],
              ["ペライチ", "LPの公開・管理（HTMLブロック埋め込み対応）", "peraichi.com", "★★★"],
              ["ST_Meta集計さん（スプシ）", "KPIデータ集約・週次月次確認", "Driveで共有", "★★★"],
              ["Claude Code", "LP作成・KPI報告・シナリオ生成を自動化", "VS Code拡張機能", "★★☆"],
              ["BigQuery", "Meta広告データのSQL分析・クリエイティブ評価", "bigquery-jukust", "★★☆"],
          ],
          row_height=0.48)

# Claude Codeスキル
add_rect(s, 0.3, 5.3, 12.7, 2.05, fill_color=C_LIGHT_GREY)
add_label(s, "Claude Code スキル一覧（呼び出しキーワード）", 0.3, 5.3, 12.7, 0.38, C_DARK_BLUE)
skills = [
    ("kpi-report",       "「KPI報告して」「週次報告」",         "BQ→グラフ→スプシ書き込みを自動化"),
    ("create-scenario",  "「シナリオ作って」",                 "月別季節変数×訴求軸でシナリオ生成"),
    ("lp-copy-variants", "「コピーを複数案作って」",            "5訴求軸でコピーセット生成"),
    ("lp-create",        "「LPを作って」",                     "競合スクショ→分析→HTML生成"),
    ("canva-story-design","「Canvaのデザインを編集して」",      "Canva API経由でStories直接編集"),
]
for i, (skill, kw, desc) in enumerate(skills):
    x = 0.5 + (i % 3) * 4.1
    y = 5.8 + (i // 3) * 0.55
    add_rect(s, x, y, 1.2, 0.38, fill_color=C_MID_BLUE)
    add_text(s, skill, x, y + 0.05, 1.2, 0.3, font_size=9, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text(s, f"{kw} → {desc}", x + 1.25, y + 0.06, 2.7, 0.3, font_size=9, color=C_BLACK)

# ═══════════════════════════════════════════════════════════
# SLIDE 8: クリエイティブ命名規則
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "クリエイティブ命名規則", "命名規則マスタ準拠・自己解釈禁止")

# フォーマット説明
add_rect(s, 0.3, 1.15, 12.7, 1.2, fill_color=C_DARK_BLUE)
add_text(s, "命名フォーマット:", 0.6, 1.2, 3.0, 0.35, font_size=12, bold=True, color=C_GREY)
add_text(s, "[通し番号][訴求軸略称]_[動画内容]_[コンテンツ種別]_[展開区分]",
         0.6, 1.55, 12.2, 0.6, font_size=18, bold=True, color=C_WHITE)

add_text(s, "例: 01タイパ_夏の予定優先×働きやすさ_ブランド診断_新規",
         0.6, 2.5, 12.0, 0.45, font_size=14, color=C_LIGHT_BLUE)

# テーブル
add_table(s, 0.3, 3.05, 12.7,
          ["要素", "意味", "例"],
          [
              ["通し番号（01, 02...）", "広告の通し番号。同一キャンペーン内で昇順", "01, 02, 03..."],
              ["訴求軸略称", "ターゲットの課題・欲求を端的に表したラベル", "タイパ / 単願 / 出費ピンチ"],
              ["動画内容", "動画フック・本文で伝える内容を具体的に", "夏の予定優先×働きやすさ"],
              ["コンテンツ種別", "利用したコンテンツ（LP内のCTAやコンテンツ名）", "ブランド診断 / LINE登録"],
              ["展開区分", "新規制作 or 既存からの横展開", "新規 / 横展開"],
          ],
          row_height=0.55)

add_rect(s, 0.3, 6.85, 12.7, 0.55, fill_color=RGBColor(0xFF, 0xEC, 0xEC))
add_text(s, "⚠ 注意: 命名規則の解釈は knowledge/creative/meta-ads-naming.md のマスタ準拠。自己解釈禁止。",
         0.5, 6.89, 12.3, 0.45, font_size=11, bold=True, color=C_RED)

# ═══════════════════════════════════════════════════════════
# SLIDE 9: 引き継ぎ時点の状況
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "⑥ 引き継ぎ時点の状況", "B2キャンペーン停止経緯・現在の課題")

# B2停止経緯
add_rect(s, 0.3, 1.15, 7.8, 4.2, fill_color=C_WHITE,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "B2キャンペーン 停止経緯（LP検証）", 0.3, 1.15, 7.8, 0.38, RGBColor(0xC0, 0x39, 0x2B))
b2_items = [
    ("キャンペーン名", "【ST-ASC】LINE友だち獲得_コンバージョン[顕在_診断_6月W1_B2]"),
    ("配信期間",      "2026-08-21〜08-25（5日間）"),
    ("消化額",        "¥25,063"),
    ("CV（BQ値）",    "2件（管理画面上は0件 ← ビュースルーCV混入）"),
    ("判定",          "クリックスルーCV=0件。停止決定（成果不足）"),
    ("ベンチマーク",   "B2なし同名広告 CPA ¥27,843 / CVR 0.75%"),
]
for i, (k, v) in enumerate(b2_items):
    y = 1.65 + i * 0.55
    add_text(s, k, 0.5, y, 1.7, 0.35, font_size=10, bold=True, color=C_MID_BLUE)
    add_text(s, v, 2.25, y, 5.7, 0.35, font_size=11, color=C_BLACK)

# 原因分析
add_text(s, "▼ 成果不足の主因（LP × クリエイティブ整合性ミスマッチ）",
         0.5, 4.2, 7.5, 0.3, font_size=11, bold=True, color=RGBColor(0xC0, 0x39, 0x2B))
mismatch = [
    "「働きやすさ担保」訴求 → FVに「働きやすさ」の回答が存在しない",
    "「夏の予定を優先」訴求 → LP全体に季節感ゼロ",
    "「出費ピンチ」訴求　 → 金銭メリット（高時給等）の提示がない",
]
for i, t in enumerate(mismatch):
    add_text(s, f"・ {t}", 0.5, 4.58 + i * 0.35, 7.5, 0.33, font_size=10, color=C_BLACK)

# 右: 推奨アクション
add_rect(s, 8.3, 1.15, 4.7, 6.2, fill_color=C_LIGHT_GREY,
         line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
add_label(s, "推奨アクション（優先度順）", 8.3, 1.15, 4.7, 0.38, C_MID_BLUE)
actions = [
    ("① 最優先", "Meta管理画面でB2キャンペーンを停止する"),
    ("② 計測修正", "管理画面のアトリビューション設定を\n「28日クリック+1日視聴」に変更"),
    ("③ BQバグ対応", "Meta Business Managerで\ncustom_cv_2のイベント設定を確認・修正"),
    ("④ 次回LP検証", "「働きやすさ」対応LP or\n「金銭メリット」FVを追加したLP変種を作成"),
    ("⑤ 運用継続", "B2なし 6月W1キャンペーンで\n同名広告の配信継続を検討"),
]
for i, (label, action) in enumerate(actions):
    y = 1.65 + i * 1.1
    add_rect(s, 8.5, y, 1.3, 0.55, fill_color=C_MID_BLUE)
    add_text(s, label, 8.5, y + 0.08, 1.3, 0.4,
             font_size=10, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text(s, action, 9.9, y + 0.02, 2.9, 0.65, font_size=10, color=C_BLACK)

# ═══════════════════════════════════════════════════════════
# SLIDE 10: 参考リンク集
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "⑦ 参考リンク集", "日常業務で参照するリンク・ドキュメント")

links = [
    ("データ・計測",      [
        ("ST_Meta集計さん（KPIスプシ）",      "1JD-Sj6Kf2yWFOTrVfV9QcwUzDJ0DVum1EwFYLiXi9Lc"),
        ("BigQuery プロジェクト",              "bigquery-jukust（VSCode / BQ Console）"),
        ("オンボーディングスプシ",             "1UakK5ig5spCTQmgdrd32XsJjiHLyAmGhymb1B5o-i8s"),
    ]),
    ("引き継ぎドキュメント", [
        ("ST Meta広告 運用引き継ぎ資料（Doc）", "1SMif6xhjyJ0OMj0iRKXXn9pDJNmAvvpvt9Sv1wn8Q7Q"),
        ("B2キャンペーン 調査まとめ（Doc）",    "1gyK83lyLTD386TQwY332ZcmeH9edTt_fxTWJFSVj2Ls"),
        ("LPO 新規検証 スプシ（深掘り分析）",   "1JD-Sj6Kf2yWFOTrVfV9QcwUzDJ0DVum1EwFYLiXi9Lc"),
    ]),
    ("Claude Code スキル", [
        ("kpi-report スキル定義",   ".claude/skills/kpi-report/SKILL.md"),
        ("create-scenario スキル",  ".claude/skills/create-scenario/SKILL.md"),
        ("命名規則マスタ",           "knowledge/creative/meta-ads-naming.md"),
        ("BigQueryスキーマ",         "knowledge/data/bigquery-schema.md"),
    ]),
]

for ci, (category, items) in enumerate(links):
    x = 0.3 + ci * 4.35
    add_rect(s, x, 1.15, 4.15, 6.2, fill_color=C_WHITE,
             line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
    add_label(s, category, x, 1.15, 4.15, 0.38, C_MID_BLUE)
    for i, (name, link) in enumerate(items):
        y = 1.65 + i * 1.1
        add_rect(s, x+0.15, y, 3.85, 0.95, fill_color=C_LIGHT_GREY)
        add_text(s, name, x+0.25, y+0.05, 3.65, 0.35, font_size=11, bold=True, color=C_DARK_BLUE)
        add_text(s, link, x+0.25, y+0.48, 3.65, 0.4, font_size=9, color=C_GREY)

# ═══════════════════════════════════════════════════════════
# SLIDE 11: エンドスライド（チェックリスト）
# ═══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_slide_header(s, "引き継ぎチェックリスト", "足立清美 確認項目")

checks = [
    ("理解レベル（Week 1）", [
        "□ STの事業概要・ビジネスモデルを説明できる",
        "□ 3ペルソナ（タイパ重視/単願/併願）と訴求軸を言える",
        "□ KPIツリー（IMP→CTR→LINE登録→応募）を把握している",
        "□ タイムラグ（中央値40日）の意味を理解している",
        "□ 週次は参考のみ・月次90日累計が本評価と理解している",
    ]),
    ("操作レベル（Week 2）", [
        "□ Meta広告管理画面にログインしてキャンペーン構造を確認できる",
        "□ Canvaでデザインを開いてテキスト変更・エクスポートできる",
        "□ ST_Meta集計さんからKPIデータを読み取れる",
        "□ 命名規則を見てクリエイティブの訴求軸を読み解ける",
        "□ Claude Code kpi-reportスキルで週次KPI報告を作成できる",
    ]),
    ("自走レベル（Month 1）", [
        "□ 直近90日累計でクリエイティブ評価を実施できる",
        "□ 「結論→根拠→アクション」形式でKPI報告を作成できる",
        "□ A/Bテストを自分で設計・実施・判定できる",
        "□ create-scenarioスキルでシナリオを生成できる",
        "□ custom_cv_2バグ対応を完了させる（Meta BM確認）",
    ]),
]

for ci, (title, items) in enumerate(checks):
    x = 0.3 + ci * 4.35
    add_rect(s, x, 1.15, 4.1, 6.2, fill_color=C_WHITE,
             line_color=RGBColor(0xCC,0xCC,0xCC), line_width=0.5)
    add_label(s, title, x, 1.15, 4.1, 0.38, C_MID_BLUE)
    for i, item in enumerate(items):
        add_text(s, item, x+0.2, 1.65 + i * 0.98, 3.8, 0.85, font_size=11, color=C_BLACK)

# 下部メッセージ
add_rect(s, 0.3, 7.1, 12.7, 0.35, fill_color=C_DARK_BLUE)
add_text(s, "わからないことはClaude Codeに聞いて。スキルとknowledgeが助けてくれる。",
         0.5, 7.13, 12.3, 0.28, font_size=12, bold=True,
         color=C_WHITE, align=PP_ALIGN.CENTER)

# ── 保存 ─────────────────────────────────────────────────
prs.save(OUTPUT)
print(f"完了: {OUTPUT}")
print(f"スライド数: {len(prs.slides)}")
