"""Google Doc + Spreadsheetの内容を取得する"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
]

DOC_ID   = "1gyK83lyLTD386TQwY332ZcmeH9edTt_fxTWJFSVj2Ls"
SHEET_ID = "1JD-Sj6Kf2yWFOTrVfV9QcwUzDJ0DVum1EwFYLiXi9Lc"
GID      = "1125575836"

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# ── Google Doc ──────────────────────────
docs_svc = build("docs", "v1", credentials=creds, cache_discovery=False)
doc = docs_svc.documents().get(documentId=DOC_ID).execute()
title = doc.get("title", "")
print(f"=== Doc: {title} ===")

lines = []
for block in doc.get("body", {}).get("content", []):
    para = block.get("paragraph", {})
    style = para.get("paragraphStyle", {}).get("namedStyleType", "")
    text = "".join(
        e.get("textRun", {}).get("content", "")
        for e in para.get("elements", [])
    ).rstrip("\n")
    if text.strip():
        prefix = "# " if "HEADING_1" in style else \
                 "## " if "HEADING_2" in style else \
                 "### " if "HEADING_3" in style else ""
        lines.append(prefix + text)

doc_text = "\n".join(lines)
print(doc_text[:3000])
print("...(以下省略)" if len(doc_text) > 3000 else "")

out_doc = "/Users/119322/Desktop/claude-code-template_af/scripts/data/research_doc.txt"
with open(out_doc, "w", encoding="utf-8") as f:
    f.write(doc_text)
print(f"\nDoc全文保存: {out_doc} ({len(lines)}行)")

# ── Spreadsheet ─────────────────────────
sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
meta = sheets_svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()

# GIDからタブ名を特定
tab_name = None
for s in meta.get("sheets", []):
    if str(s["properties"]["sheetId"]) == GID:
        tab_name = s["properties"]["title"]
        break

print(f"\n=== Sheet タブ: {tab_name} (gid={GID}) ===")

# 全タブ一覧も出力
print("全タブ:", [s["properties"]["title"] for s in meta.get("sheets", [])])

result = sheets_svc.spreadsheets().values().get(
    spreadsheetId=SHEET_ID,
    range=f"'{tab_name}'",
    valueRenderOption="FORMATTED_VALUE",
).execute()
rows = result.get("values", [])
print(f"行数: {len(rows)}")

for i, row in enumerate(rows[:60]):
    print(f"  {i+1:3d}: {' | '.join(str(c) for c in row[:8])}")

out_sheet = "/Users/119322/Desktop/claude-code-template_af/scripts/data/research_sheet.json"
with open(out_sheet, "w", encoding="utf-8") as f:
    json.dump({"tab": tab_name, "rows": rows}, f, ensure_ascii=False, indent=2)
print(f"\nSheet保存: {out_sheet} ({len(rows)}行)")
