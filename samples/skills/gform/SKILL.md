---
name: gform
description: 「フォーム作って」「Googleフォーム作成」「アンケート作って」「申し込みフォーム作って」など、Googleフォームを新規作成するときに発動。
---

## 概要

ユーザーの指示をもとにGoogleフォームを作成し、URLを返す。

---

## STEP 1: 情報収集

以下を確認する（渡されていなければ聞く）：

- フォームのタイトル・説明文
- 質問一覧（質問文・種類・必須かどうか）

**質問の種類：**

| 種類 | typeキー |
|---|---|
| 記述式（短文） | `SHORT_ANSWER` |
| 段落（長文） | `PARAGRAPH` |
| ラジオボタン（1択） | `RADIO` |
| チェックボックス（複数選択） | `CHECKBOX` |
| プルダウン | `DROP_DOWN` |
| 日付 | `DATE` |
| 時刻 | `TIME` |

---

## STEP 2: 認証

```python
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"{{PROJECT_ROOT}}\secrets\token.json"
SCOPES = ["https://www.googleapis.com/auth/forms.body"]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds.valid and creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
token = creds.token
```

---

## STEP 3: フォーム作成

```python
body = json.dumps({
    "info": {
        "title": "{フォームタイトル}",
        "documentTitle": "{フォームタイトル}"
    }
}).encode("utf-8")

req = urllib.request.Request(
    "https://forms.googleapis.com/v1/forms",
    data=body,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    form = json.loads(resp.read().decode("utf-8"))

form_id = form["formId"]
print(f"フォームID: {form_id}")
print(f"編集URL: https://docs.google.com/forms/d/{form_id}/edit")
print(f"回答URL: https://docs.google.com/forms/d/{form_id}/viewform")
```

---

## STEP 4: 説明文・質問を追加（batchUpdate）

```python
requests = []

# 質問を追加（SHORT_ANSWER の例）
requests.append({
    "createItem": {
        "item": {
            "title": "{質問文}",
            "questionItem": {
                "question": {
                    "required": True,
                    "textQuestion": {"paragraph": False}
                }
            }
        },
        "location": {"index": 0}
    }
})

batch_body = json.dumps({"requests": requests}).encode("utf-8")
req2 = urllib.request.Request(
    f"https://forms.googleapis.com/v1/forms/{form_id}:batchUpdate",
    data=batch_body,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req2) as resp:
    json.loads(resp.read().decode("utf-8"))
print("質問追加完了")
```
