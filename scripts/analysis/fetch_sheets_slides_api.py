"""
Google Sheets API + Slides API でデータを取得する
必要: pip install google-auth google-auth-oauthlib google-api-python-client requests
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json, os, requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE  = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
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
GID        = "661700305"          # タブID
PRES_ID    = "1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0"
SLIDE_PAGE = "slide13"            # スライドページID (g... 形式の可能性あり)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────
# 認証
# ─────────────────────────────────────────
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# ─────────────────────────────────────────
# 1. スプレッドシート：タブ名を特定してデータ取得
# ─────────────────────────────────────────
sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

# まずシートメタ情報でGIDからシート名を特定
meta = sheets_svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
target_sheet_name = None
for s in meta.get("sheets", []):
    props = s.get("properties", {})
    if str(props.get("sheetId")) == GID:
        target_sheet_name = props.get("title")
        break

print(f"対象タブ: {target_sheet_name} (gid={GID})")

if target_sheet_name:
    result = sheets_svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"'{target_sheet_name}'",
        valueRenderOption="FORMATTED_VALUE",
    ).execute()
    rows = result.get("values", [])
else:
    rows = []

print(f"シート行数: {len(rows)}")
# 保存
sheet_out = os.path.join(OUTPUT_DIR, "compare_sheet_data.json")
with open(sheet_out, "w", encoding="utf-8") as f:
    json.dump({"sheet_name": target_sheet_name, "rows": rows}, f, ensure_ascii=False, indent=2)
print(f"シートデータ保存: {sheet_out}")

# ─────────────────────────────────────────
# 2. スライド：全スライドの構造取得＋スライド13のサムネイル取得
# ─────────────────────────────────────────
slides_svc = build("slides", "v1", credentials=creds, cache_discovery=False)
pres = slides_svc.presentations().get(presentationId=PRES_ID).execute()

slides = pres.get("slides", [])
print(f"\nスライド総数: {len(slides)}")

# slide13 をインデックス・objectId の両方から探す
target_slide = None
for i, slide in enumerate(slides):
    oid = slide.get("objectId", "")
    # "slide13" がobjectIdに含まれる、またはインデックスが12（0始まり）
    if oid == SLIDE_PAGE or oid.lower() == SLIDE_PAGE.lower():
        target_slide = slide
        slide_index = i
        break
    if i == 12:   # 13枚目（0始まり）
        target_slide = slide
        slide_index = i

if target_slide is None:
    print("slide13 が見つからなかったため13枚目（index=12）を使用")
    target_slide = slides[12] if len(slides) > 12 else slides[-1]
    slide_index = 12

slide_oid = target_slide.get("objectId")
print(f"対象スライド objectId: {slide_oid}  (index={slide_index})")

# スライドのテキスト要素を抽出
def extract_slide_texts(slide):
    texts = []
    for elem in slide.get("pageElements", []):
        shape = elem.get("shape", {})
        text_content = shape.get("text", {})
        for te in text_content.get("textElements", []):
            tr = te.get("textRun", {})
            content = tr.get("content", "").strip()
            if content:
                texts.append(content)
    return texts

slide_texts = extract_slide_texts(target_slide)
print(f"\nスライド13テキスト ({len(slide_texts)}件):")
for t in slide_texts:
    print(f"  - {t}")

# スライドのサムネイル画像を取得
thumb_resp = slides_svc.presentations().pages().getThumbnail(
    presentationId=PRES_ID,
    pageObjectId=slide_oid,
    thumbnailProperties_thumbnailSize="LARGE",
).execute()
thumb_url = thumb_resp.get("contentUrl")
print(f"\nサムネイルURL取得: {thumb_url[:80]}...")

# 画像をダウンロード
if thumb_url:
    img_resp = requests.get(thumb_url, timeout=30)
    img_path = os.path.join(OUTPUT_DIR, "compare_slide13.png")
    with open(img_path, "wb") as f:
        f.write(img_resp.content)
    print(f"スライド画像保存: {img_path}")

# スライドデータをJSONに保存
slide_out = os.path.join(OUTPUT_DIR, "compare_slide13_data.json")
with open(slide_out, "w", encoding="utf-8") as f:
    json.dump({"slide_index": slide_index, "objectId": slide_oid, "texts": slide_texts}, f, ensure_ascii=False, indent=2)
print(f"スライドデータ保存: {slide_out}")

# ─────────────────────────────────────────
# 3. サマリー出力
# ─────────────────────────────────────────
print("\n" + "="*60)
print("【シートデータ（先頭20行）】")
for row in rows[:20]:
    print("  |".join(str(c) for c in row[:10]))

print("\n【スライド13 テキスト全文】")
for t in slide_texts:
    print(f"  {t}")
