"""全スライドのテキストとobjectIdを取得する"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = ['https://www.googleapis.com/auth/presentations',
          'https://www.googleapis.com/auth/drive']
PRES_ID = "1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0"

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
svc   = build("slides", "v1", credentials=creds, cache_discovery=False)
pres  = svc.presentations().get(presentationId=PRES_ID).execute()

slides = pres.get("slides", [])
print(f"総スライド数: {len(slides)}\n")

result = []
for i, slide in enumerate(slides):
    oid = slide.get("objectId", "")
    texts = []
    for elem in slide.get("pageElements", []):
        shape = elem.get("shape", {})
        for te in shape.get("text", {}).get("textElements", []):
            c = te.get("textRun", {}).get("content", "").strip()
            if c:
                texts.append(c)
    print(f"[{i+1:02d}] {oid}")
    for t in texts:
        print(f"     {t}")
    result.append({"index": i+1, "objectId": oid, "texts": texts})

out = "/Users/119322/Desktop/claude-code-template_af/scripts/data/slides_all.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nJSON保存: {out}")
