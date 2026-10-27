"""更新後のスライド全体を確認する"""
import sys, io, requests as req_lib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']
PRES_ID = "1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0"

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
svc   = build("slides", "v1", credentials=creds, cache_discovery=False)
pres  = svc.presentations().get(presentationId=PRES_ID).execute()

slides = pres.get("slides", [])
print(f"総スライド数: {len(slides)}\n")

for i, slide in enumerate(slides):
    oid = slide.get("objectId", "")
    texts = []
    for elem in slide.get("pageElements", []):
        shape = elem.get("shape", {})
        for te in shape.get("text", {}).get("textElements", []):
            c = te.get("textRun", {}).get("content", "").strip()
            if c:
                texts.append(c)
    title = texts[0] if texts else "(no text)"
    print(f"[{i+1:02d}] {oid:30s} | {title[:60]}")

# 新スライド2枚のサムネイル保存
import os
OUTPUT_DIR = "/Users/119322/Desktop/claude-code-template_af/scripts/data"
for oid, name in [
    ("new_slide_kpi_targets", "verify_kpi_targets"),
    ("new_slide_action_flow",  "verify_action_flow"),
]:
    thumb = svc.presentations().pages().getThumbnail(
        presentationId=PRES_ID,
        pageObjectId=oid,
        thumbnailProperties_thumbnailSize="LARGE",
    ).execute()
    url = thumb.get("contentUrl")
    r = req_lib.get(url, timeout=20)
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    with open(path, "wb") as f:
        f.write(r.content)
    print(f"\nサムネイル保存: {path}")
