---
name: gdoc
description: 「ドキュメントにして」「Googleドキュメントに整形して」「ドキュメント化して」など、分析結果や資料をGoogleドキュメントとして作成・整形したいときに発動。表・見出し・色付きセルを含む整形済みドキュメントを作成する。
---

## 概要

このスキルは以下を一括実行する：
1. Googleドキュメントを新規作成
2. 見出し・段落・表を整形（ヘッダー行に背景色、罫線あり）
3. ドキュメントのURLを返す

---

## STEP 1: 認証

```python
import sys, io, os, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]
TOKEN_FILE = r'{{PROJECT_ROOT}}\secrets\token.json'
CREDS_FILE = r'{{PROJECT_ROOT}}\secrets\credentials.json'

creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except:
            creds = None
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

token = creds.token

def api(url, body=None, method=None):
    data = json.dumps(body).encode('utf-8') if body else None
    m = method or ('POST' if data else 'GET')
    req = urllib.request.Request(url, data=data,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method=m)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))
```

---

## STEP 2: ドキュメント作成

```python
title = '（タイトルを指定）'
doc = api('https://docs.googleapis.com/v1/documents', {'title': title})
doc_id = doc['documentId']
```

---

## STEP 3: コンテンツ挿入 + 整形

### 基本方針
- コンテンツは **まず insertText でテキストを一括挿入**し、その後 batchUpdate で書式を適用する
- インデックスはドキュメント末尾から逆順に挿入すると位置ズレが起きない
- 表は `insertTable` リクエストで作成し、セルへの書き込みは `insertText` で行う

### 見出しスタイルの適用

```python
{
    'updateParagraphStyle': {
        'range': {'startIndex': start, 'endIndex': end},
        'paragraphStyle': {'namedStyleType': 'HEADING_1'},
        'fields': 'namedStyleType'
    }
}
```

### 表の挿入

```python
{
    'insertTable': {
        'rows': rows,
        'columns': columns,
        'location': {'index': insert_index}
    }
}
```

### batchUpdate の実行

```python
api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
    {'requests': requests_list})
```

---

## STEP 4: URL を返す

```python
url = f'https://docs.google.com/document/d/{doc_id}/edit'
print(f'{title}')
print(f'URL: {url}')
```

---

## 注意事項

- `insertText` でテキストを挿入した後に書式を適用する（逆はNG）
- インデックスはドキュメント内の文字位置。改行も1文字としてカウント
- 大きなドキュメントは batchUpdate を複数回に分けて実行する（1回あたり最大50リクエスト推奨）
- token が `documents` スコープを持っていない場合は再認証が必要
