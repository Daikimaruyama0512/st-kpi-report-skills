---
name: gdrive
description: ユーザーがGoogle Driveのファイル一覧を見たい、ファイルを探したい、「ドライブ」「Drive」「Googleドライブ」などと言ったときに発動する。ファイルの検索・一覧表示を行う。
---

⚠️ `mcp__gdrive__search` や `ReadMcpResourceTool(gdrive)` は **Service Account認証** のため個人のDriveファイルにアクセスできない。必ず以下の **token.json（OAuth2）方式** を使うこと。

## Google Driveファイルを検索・読む方法

### ファイル検索

```python
import subprocess, sys, io, json, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]
TOKEN_FILE = r"{{PROJECT_ROOT}}\secrets\token.json"
CREDS_FILE = r"{{PROJECT_ROOT}}\secrets\credentials.json"

creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token

query = "{{検索キーワード}}"
params = urllib.parse.urlencode({
    "q": f"name contains '{query}' and trashed=false",
    "fields": "files(id,name,mimeType,modifiedTime)",
    "pageSize": 20
})
url = f"https://www.googleapis.com/drive/v3/files?{params}"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode("utf-8"))

for f in result.get("files", []):
    print(f["name"], "|", f["id"], "|", f.get("mimeType",""), "|", f.get("modifiedTime","")[:10])
```

---

### Google Docsファイルの内容を読む

```python
file_id = "{{FILE_ID}}"
url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as resp:
    text = resp.read().decode("utf-8-sig")
sys.stdout.buffer.write(text[:5000].encode("utf-8"))
sys.stdout.buffer.write(b"\n")
sys.stdout.buffer.flush()
```

引数なし（全件）の場合は `q` を `"trashed=false"` にする。

---

## 表示フォーマット

```
Google Drive 検索結果: "<クエリ>"
─────────────────────────────────────
[アイコン] ファイル名
           種類: Google Docs / スプレッドシート / フォルダ / PDFなど
           更新日: YYYY-MM-DD
─────────────────────────────────────
合計: N 件
```

ファイル種別のアイコン対応:
- フォルダ → フォルダ
- Google ドキュメント → Doc
- Google スプレッドシート → Sheet
- Google スライド → Slide
- PDF → PDF
- その他 → File

結果が0件の場合は「該当するファイルが見つかりませんでした。」と表示し、別のキーワードを提案する。
