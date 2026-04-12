---
name: write-sheet
description: 「スプシに書いて」「スプレッドシートに記入して」「シートに追加して」など、Googleスプレッドシートへの書き込みを依頼されたときに発動。MCPツールでスプレッドシートに書き込む。
---

## 書き込み方法（MCP）

データの書き込みには `mcp__google_sheets__update_cells` を使う。Pythonスクリプトは不要。

### 基本的な書き込み
```
mcp__google_sheets__update_cells を呼び出す:
  - spreadsheet_id: 対象のスプレッドシートID
  - range: "シート名!A{行番号}"（例: "投稿案!A3"）
  - values: [[列1, 列2, ...]]（2次元配列）
```

### 複数セルの一括書き込み
```
mcp__google_sheets__batch_update_cells を呼び出す:
  - spreadsheet_id: 対象のスプレッドシートID
  - data: [{"range": "シート名!A1", "values": [[...]]}, ...]
```

## 対象スプレッドシート

書き込み先のスプレッドシートIDはユーザーに確認する。

## 書き込み前に必ず確認する

- どのシートの何行目に書くか、ユーザーに確認してから書き込む
- シート指定がない場合は「どのシートに書きますか？」と聞く

## 書式設定・グラフ作成が必要な場合（Python fallback）

MCPツールではセル書式設定（背景色・罫線・セル結合）やグラフ作成はできない。
これらが必要な場合のみ、以下のPython方式を使う。

### 書式設定（batchUpdate）
```python
import json, urllib.request
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"{{PROJECT_ROOT}}\secrets\token.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds.valid and creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
token = creds.token

SPREADSHEET_ID = "対象のスプレッドシートID"
body = {"requests": [ ... ]}  # repeatCell, mergeCells 等
data = json.dumps(body).encode("utf-8")
url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
req = urllib.request.Request(url, data=data, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}, method="POST")
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode("utf-8"))
```

**注意**: マージ済みセルがある場合は先に `unmergeCells` してから `mergeCells`。

### グラフ作成（addChart）

`urllib.request` で直接 Sheets API を叩く。

```python
import json, urllib.request
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"{{PROJECT_ROOT}}\secrets\token.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds.valid and creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
token = creds.token

SPREADSHEET_ID = "対象のスプレッドシートID"

# まずシートIDを取得
url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets.properties"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as resp:
    meta = json.loads(resp.read().decode("utf-8"))
# シート名で絞る場合: next(s for s in meta["sheets"] if s["properties"]["title"] == "シート名")
sheet_id = meta["sheets"][0]["properties"]["sheetId"]

# addChart リクエスト
body = {
    "requests": [{
        "addChart": {
            "chart": {
                "spec": {
                    "title": "グラフタイトル",
                    "basicChart": {
                        "chartType": "COLUMN",  # BAR / LINE / PIE なども可
                        "legendPosition": "BOTTOM_LEGEND",
                        "axis": [
                            {"position": "BOTTOM_AXIS", "title": "X軸ラベル"},
                            {"position": "LEFT_AXIS", "title": "Y軸ラベル"}
                        ],
                        "domains": [{
                            "domain": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": sheet_id,
                                        "startRowIndex": 0,
                                        "endRowIndex": 7,
                                        "startColumnIndex": 0,
                                        "endColumnIndex": 1
                                    }]
                                }
                            }
                        }],
                        "series": [{
                            "series": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": sheet_id,
                                        "startRowIndex": 0,
                                        "endRowIndex": 7,
                                        "startColumnIndex": 1,
                                        "endColumnIndex": 2
                                    }]
                                }
                            },
                            "targetAxis": "LEFT_AXIS"
                        }],
                        "headerCount": 1
                    }
                },
                "position": {
                    "overlayPosition": {
                        "anchorCell": {
                            "sheetId": sheet_id,
                            "rowIndex": 1,
                            "columnIndex": 3
                        },
                        "widthPixels": 600,
                        "heightPixels": 400
                    }
                }
            }
        }
    }]
}

data = json.dumps(body).encode("utf-8")
url2 = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
req2 = urllib.request.Request(url2, data=data, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}, method="POST")
with urllib.request.urlopen(req2) as resp:
    result = json.loads(resp.read().decode("utf-8"))
print("グラフ作成成功:", result["replies"][0]["addChart"]["chart"]["chartId"])
```

**補足**:
- `chartType`: `COLUMN`（縦棒）/ `BAR`（横棒）/ `LINE`（折れ線）/ `PIE`（円）
- 複数系列は `series` 配列に追加する
- `mcp__google_sheets__batch_update_cells` ではグラフ作成不可。必ずこのPython方式を使う
