---
name: google-calendar
description: 「カレンダーにタスクを登録して」「リマインダーを登録して」「○○のタスクを追加して」と言われたときに発動。Google Tasks API を使用して、指定の期日にタスクをGoogleカレンダーのタスク管理機能に登録する。
---

## 概要

このスキルは以下を一括実行する：
1. Google Tasks APIの書き込み権限を確認
2. 指定の期日でタスクを新規作成
3. タイトル（title）、メモ（notes：URLなど含む）、期日（due）を設定
4. 登録完了を報告する

---

## STEP 1: 認証（token.json を使う）

```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os, json, urllib.request
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r'/Users/119322/claude-code-template_af\secrets\token.json'
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())
token = creds.token
```

---

## STEP 2: タスクの登録

```python
deadline_date = '2026-04-07'  # 期日（YYYY-MM-DD形式）
due_utc = f'{deadline_date}T00:00:00.000Z'

task = {
    'title': 'タスク名',
    'notes': 'タスク概要',
    'due': due_utc,
    'status': 'needsAction'
}

url = 'https://tasks.googleapis.com/tasks/v1/lists/%40default/tasks'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

data = json.dumps(task).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')

with urllib.request.urlopen(req) as r:
    res = json.loads(r.read().decode('utf-8'))
    print(f"タスク登録完了: {res.get('selfLink', '')}")
```

---

## 注意事項

- **期日（due）はUTC形式**: `YYYY-MM-DDT00:00:00.000Z` を指定する
- **タスクリスト**: `%40default` はデフォルトのタスクリスト
- **権限エラー (403)**: `token.json` に `tasks` スコープがない場合に発生。再認証が必要
