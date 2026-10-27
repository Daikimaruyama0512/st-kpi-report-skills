"""
Google Doc（台本）の内容を Google Slides の speaker notes に書き込むスクリプト

対象Doc : 新井さん向け オンボーディング台本
          https://docs.google.com/document/d/1SVe31BkhjTV0p-GYdMyMa5csdeUIGo8rZ7-dMdVZyo0/edit
対象Pres: オンボーディングスライド
          https://docs.google.com/presentation/d/1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0/edit

必要: pip install google-api-python-client google-auth
"""
import sys, io, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = "/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
]

DOC_ID  = "1SVe31BkhjTV0p-GYdMyMa5csdeUIGo8rZ7-dMdVZyo0"
PRES_ID = "1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0"

# ── 認証 ─────────────────────────────────────────────────────────────
print("認証中...")
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

drive_svc  = build("drive",  "v3", credentials=creds, cache_discovery=False)
slides_svc = build("slides", "v1", credentials=creds, cache_discovery=False)

# ── Google Doc をテキストでエクスポート ──────────────────────────────
print(f"Google Doc を取得中: {DOC_ID}")
raw = drive_svc.files().export(fileId=DOC_ID, mimeType="text/plain").execute()
text = raw.decode("utf-8").replace('\r\n', '\n').lstrip('\ufeff')

# ── スライドセクションに分割 ─────────────────────────────────────────
# 「▼ スライドXX: 」で分割（セクション数 = スライド数 × 2 + 1）
parts = re.split(r'(▼ スライド\d+: )', text)
# parts = [前文, "▼ スライド01: ", "本文01", "▼ スライド02: ", "本文02", ...]

def clean_notes(header: str, body: str) -> str:
    """
    各スライドのノートテキストを整形する。
    - ヘッダー行（スライド番号・ID表記）は除去
    - [スライド本文（参照）] ブロックは除去（narrationだけ残す）
    - 区切り線（────...）は除去
    - 行末の余分な空白を除去
    """
    full = header + body

    # ヘッダー行（▼ スライドXX: タイトル  (ID: xxxxx)）を除去
    full = re.sub(r'^▼ スライド\d+:.+\(ID: \S+\)\s*\n', '', full)

    # [スライド本文（参照）] ブロックを除去（次のブロックまで）
    full = re.sub(r'\[スライド本文（参照）\].*?(?=【|─{3,}|\Z)', '', full, flags=re.DOTALL)

    # 区切り線（────...）を除去
    full = re.sub(r'─{10,}\n?', '', full)

    # 「━」の区切りを除去
    full = re.sub(r'━{10,}\n?', '', full)

    # 3行以上の連続空行を最大2行に圧縮
    full = re.sub(r'\n{3,}', '\n\n', full)

    return full.strip()


# スライドごとの notes テキストを構築
slide_notes = []  # [(slide_index_0based, notes_text), ...]

for i in range(1, len(parts) - 1, 2):
    header  = parts[i]      # "▼ スライド01: "
    body    = parts[i + 1]  # "オープニング  (ID: slide01)\n\n..."

    # セクション区切り（次の▼スライドの前まで）が本文に含まれる場合はトリム
    # （re.split が正しく分割しているので基本不要だが念のため）
    body = re.split(r'▼ スライド\d+: ', body)[0]

    notes_text = clean_notes(header, body)
    slide_index = (i - 1) // 2  # 0始まり
    slide_notes.append((slide_index, notes_text))
    print(f"  スライド{slide_index+1:02d}: {len(notes_text)}文字")

print(f"\n合計 {len(slide_notes)} スライド分の notes を解析完了")

# ── Slides API でプレゼンテーション取得 ─────────────────────────────
print(f"\nプレゼンテーション取得中: {PRES_ID}")
pres   = slides_svc.presentations().get(presentationId=PRES_ID).execute()
slides = pres.get("slides", [])
print(f"  → {len(slides)} 枚のスライドを取得")

# スライドごとの notes body objectId と既存テキスト長を収集
notes_obj_ids = {}     # slide_index → objectId
notes_has_text = {}    # slide_index → bool（既存テキストがあるか）
for idx, slide in enumerate(slides):
    notes_page = slide.get("slideProperties", {}).get("notesPage", {})
    for elem in notes_page.get("pageElements", []):
        ph = elem.get("shape", {}).get("placeholder", {})
        if ph.get("type") == "BODY":
            notes_obj_ids[idx] = elem["objectId"]
            # text フィールドが存在しかつ要素がある場合のみ既存テキストありとみなす
            text_content = elem.get("shape", {}).get("text", {}).get("textElements", [])
            notes_has_text[idx] = len(text_content) > 0
            break

# ── speaker notes を書き込む ─────────────────────────────────────────
print("\nSpeaker notes を書き込み中...")
requests = []

for slide_index, notes_text in slide_notes:
    if slide_index >= len(slides):
        print(f"  ⚠ スライド{slide_index+1} は存在しないためスキップ")
        continue
    obj_id = notes_obj_ids.get(slide_index)
    if not obj_id:
        print(f"  ⚠ スライド{slide_index+1} の notes objectId が見つからないためスキップ")
        continue

    # 既存テキストがある場合のみ削除（空ノートへのdeleteTextはAPIエラーになるため）
    if notes_has_text.get(slide_index, False):
        requests.append({
            "deleteText": {
                "objectId": obj_id,
                "textRange": {"type": "ALL"}
            }
        })
    if notes_text:
        requests.append({
            "insertText": {
                "objectId": obj_id,
                "insertionIndex": 0,
                "text": notes_text
            }
        })

if requests:
    # Slides API は一度に大量のリクエストを送ると429になる場合があるので分割
    chunk_size = 20
    for i in range(0, len(requests), chunk_size):
        chunk = requests[i:i + chunk_size]
        slides_svc.presentations().batchUpdate(
            presentationId=PRES_ID,
            body={"requests": chunk}
        ).execute()
        if i + chunk_size < len(requests):
            time.sleep(0.5)
    print(f"  → {len(slide_notes)} スライドへの書き込み完了（{len(requests)} リクエスト）")
else:
    print("  書き込むリクエストがありません")

url = f"https://docs.google.com/presentation/d/{PRES_ID}/edit"
print(f"\n完成URL: {url}")
