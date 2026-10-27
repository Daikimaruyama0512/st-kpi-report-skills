"""
オンボーディングスライドをスプレッドシート補完内容に合わせて更新する
対象: 1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
]
PRES_ID = "1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0"

# スライド寸法 (16:9 標準 EMU)
W = 9144000
H = 5143500
MARGIN = 457200   # 約0.5インチ

# クリームカラー (LP背景と統一: #FAE2D1)
BG_CREAM  = {"red": 0.980, "green": 0.886, "blue": 0.820}
# オレンジ (#FF7019)
ORANGE    = {"red": 1.0, "green": 0.439, "blue": 0.098}
# 白
WHITE     = {"red": 1.0, "green": 1.0, "blue": 1.0}
# 濃いグレー
DARK      = {"red": 0.15, "green": 0.15, "blue": 0.15}

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
svc   = build("slides", "v1", credentials=creds, cache_discovery=False)

# ────────────────────────────────────────────
# ヘルパー: テキストボックスを作成するリクエスト群を返す
# ────────────────────────────────────────────
def make_textbox(obj_id, page_id, text, x, y, w, h,
                 font_size=14, bold=False, color=None):
    color = color or DARK
    reqs = [
        {
            "createShape": {
                "objectId": obj_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": page_id,
                    "size": {
                        "width":  {"magnitude": w, "unit": "EMU"},
                        "height": {"magnitude": h, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": x, "translateY": y,
                        "unit": "EMU",
                    },
                },
            }
        },
        {"insertText": {"objectId": obj_id, "text": text, "insertionIndex": 0}},
        {
            "updateTextStyle": {
                "objectId": obj_id,
                "style": {
                    "bold": bold,
                    "fontSize": {"magnitude": font_size, "unit": "PT"},
                    "foregroundColor": {"opaqueColor": {"rgbColor": color}},
                    "fontFamily": "Noto Sans JP",
                },
                "textRange": {"type": "ALL"},
                "fields": "bold,fontSize,foregroundColor,fontFamily",
            }
        },
        {
            "updateParagraphStyle": {
                "objectId": obj_id,
                "style": {"lineSpacing": 140},
                "textRange": {"type": "ALL"},
                "fields": "lineSpacing",
            }
        },
    ]
    return reqs


def make_slide(obj_id, insertion_index, title_text, body_text):
    """スライドを1枚作成してタイトル+本文を配置するリクエスト群を返す"""
    title_id = obj_id + "_title"
    body_id  = obj_id + "_body"
    reqs = []

    # 1. スライド挿入
    reqs.append({
        "createSlide": {
            "insertionIndex": insertion_index,
            "slideLayoutReference": {"predefinedLayout": "BLANK"},
            "objectId": obj_id,
        }
    })

    # 2. 背景をクリームに
    reqs.append({
        "updatePageProperties": {
            "objectId": obj_id,
            "pageProperties": {
                "pageBackgroundFill": {
                    "solidFill": {
                        "color": {"rgbColor": BG_CREAM}
                    }
                }
            },
            "fields": "pageBackgroundFill",
        }
    })

    # 3. オレンジの上部帯 (装飾)
    bar_id = obj_id + "_bar"
    reqs.append({
        "createShape": {
            "objectId": bar_id,
            "shapeType": "RECTANGLE",
            "elementProperties": {
                "pageObjectId": obj_id,
                "size": {
                    "width":  {"magnitude": W, "unit": "EMU"},
                    "height": {"magnitude": 457200, "unit": "EMU"},
                },
                "transform": {
                    "scaleX": 1, "scaleY": 1,
                    "translateX": 0, "translateY": 0,
                    "unit": "EMU",
                },
            },
        }
    })
    reqs.append({
        "updateShapeProperties": {
            "objectId": bar_id,
            "shapeProperties": {
                "shapeBackgroundFill": {
                    "solidFill": {"color": {"rgbColor": ORANGE}}
                },
                "outline": {"propertyState": "NOT_RENDERED"},
            },
            "fields": "shapeBackgroundFill,outline",
        }
    })

    # 4. タイトル（帯の上に白文字）
    reqs += make_textbox(
        title_id, obj_id, title_text,
        x=MARGIN, y=50000,
        w=W - MARGIN * 2, h=400000,
        font_size=26, bold=True, color=WHITE,
    )

    # 5. 本文
    reqs += make_textbox(
        body_id, obj_id, body_text,
        x=MARGIN, y=530000,
        w=W - MARGIN * 2, h=H - 530000 - MARGIN // 2,
        font_size=13, bold=False, color=DARK,
    )

    return reqs


# ────────────────────────────────────────────
# 全リクエストを積み上げる
# ────────────────────────────────────────────
requests = []

# ═══ ① スライド8 (使用ツール): スキル3つ追記 ═══
requests.append({
    "replaceAllText": {
        "containsText": {"text": "/create-scenario    Meta広告シナリオ設計"},
        "replaceText": (
            "/create-scenario    Meta広告シナリオ設計\n"
            "/write-sheet        スプシへのデータ書き込み\n"
            "/gdoc               分析結果をドキュメント化\n"
            "/ads-analyst        広告分析・クリエイティブ評価"
        ),
    }
})

# ═══ ② スライド9 (LPガイド): LP評価基準を追記 ═══
requests.append({
    "replaceAllText": {
        "containsText": {"text": "・記録: A/Bテスト計画書SSに必ず記録"},
        "replaceText": (
            "・記録: A/Bテスト計画書SSに必ず記録\n"
            "\n"
            "LP評価基準\n"
            "・CVポイント: LINE友だち追加（lin.ee経由）\n"
            "・評価サイクル: 月次（クリエイティブ評価と同タイミング）\n"
            "・改善トリガー: 応募CPA ¥30,000超 かつ 転換率<10% でLP起因を疑う"
        ),
    }
})

# ═══ ③ スライド12 (チェックリスト): 新項目を追記 ═══
requests.append({
    "replaceAllText": {
        "containsText": {"text": "□ 週次報告を上長に提出できる"},
        "replaceText": (
            "□ 週次報告を上長に提出できる\n"
            "□ LP-CVRとは何かを説明・計測できる\n"
            "□ どのスキルをどんな時に使うかを答えられる"
        ),
    }
})

# ═══ ④ AGENDAスライド: ⑥の説明を更新 ═══
requests.append({
    "replaceAllText": {
        "containsText": {"text": "⑥ 分析・KPI報告 ─ 評価の型・BigQuery"},
        "replaceText": "⑥ 分析・KPI報告 ─ KPI目標値・評価の型・アクションフロー",
    }
})

# ═══ ⑤ 新スライドA: KPI目標値 & 停止基準 (slide11の後=index11) ═══
BODY_KPI = (
    "■ 応募CPA目標\n"
    "  ≤ ¥20,000          → 良好（継続・予算引き上げを検討）\n"
    "  ¥20,001 〜 30,000  → 要観察（クリエイティブ・LP改善を検討）\n"
    "  ¥30,001 〜 40,000  → 要見直し（CTA配分・ナーチャリング改善）\n"
    "  ¥40,001 以上       → 要停止検討（理由を明確化できなければ停止）\n"
    "\n"
    "■ 転換率（LINE登録→応募）\n"
    "  ≥ 15%  → 良好　／　10〜14% → 要改善　／　< 10% → 緊急対応\n"
    "\n"
    "■ CPF（LINE登録単価）\n"
    "  顕在層（ペルソナLP等）: ¥1,500〜3,000\n"
    "  潜在層（気軽に診断等）: ¥700〜1,500\n"
    "\n"
    "■ クリエイティブ停止基準\n"
    "  ・消化 ¥15,000 超で CV 0件 → 即停止\n"
    "  ・出稿2日経過で消化 ¥1,000 未満 → 停止"
)
requests += make_slide(
    obj_id="new_slide_kpi_targets",
    insertion_index=11,
    title_text="KPI目標値 & 停止基準",
    body_text=BODY_KPI,
)

# ═══ ⑥ 新スライドB: 分析→アクション フロー (index12, Aの後) ═══
BODY_ACTION = (
    "Step 1: BigQuery で直近90日 CPA 確認（spend ≥ ¥10,000）\n"
    "Step 2: 停止判断（消化 ¥15,000 超で CV 0件 → 即停止）\n"
    "Step 3: 予算調整（月10%以上の変更は事前確認必須）\n"
    "Step 4: 新クリエイティブ企画（create-scenario スキルで起動）\n"
    "Step 5: LP改善が必要なら lp-copy-variants でコピー案を生成\n"
    "\n"
    "■ 指標別トラブルシューティング\n"
    "  CTR 低下  → クリエイティブの摩耗・インサイトのズレ\n"
    "             → 訴求軸・動画の型を入れ替え\n"
    "\n"
    "  CVR 低下  → 広告と LP の期待値ギャップ\n"
    "             → Meta〜LP〜LINE のメッセージ一貫性を確認\n"
    "\n"
    "  IMP 低下  → AI の過度な絞り込み・顕在層の枯渇\n"
    "             → ターゲット拡張・潜在層投資強化"
)
requests += make_slide(
    obj_id="new_slide_action_flow",
    insertion_index=12,
    title_text="分析→アクション フロー",
    body_text=BODY_ACTION,
)

# ────────────────────────────────────────────
# batchUpdate 実行
# ────────────────────────────────────────────
print(f"リクエスト数: {len(requests)}")
resp = svc.presentations().batchUpdate(
    presentationId=PRES_ID,
    body={"requests": requests},
).execute()

replies = resp.get("replies", [])
print(f"完了 ({len(replies)} 件の応答)")
print("確認URL:")
print(f"https://docs.google.com/presentation/d/{PRES_ID}/edit")
