---
# ===== サンプル: 朝ブリーフィングスキル =====
# 参考パターン: カレンダー + タスクスプシの統合
name: morning-briefing
description: "「おはよう」「おはようございます」と言ったときに発動。今日のカレンダー予定とタスク一覧を統合してブリーフィングを表示する。"
---

## 処理フロー

1. Google Calendar APIで当日の予定を取得
2. タスク管理ファイル（またはスプレッドシート）から未完了タスクを取得
3. 以下のフォーマットで出力

## 出力フォーマット

```
## おはようございます！ 今日は YYYY年MM月DD日 です。

### 今日の予定
- HH:MM 〇〇ミーティング
- HH:MM △△定例

### 未完了タスク
- [優先] タスク名（期限: MM/DD）
- [通常] タスク名

### 今日のフォーカス
（予定とタスクから判断した今日の重点事項）
```

## カレンダー取得コード例

```python
import json, urllib.request
# token.json を使って Calendar API を叩く
url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
params = f"?timeMin={today_start}&timeMax={today_end}&singleEvents=true&orderBy=startTime"
req = urllib.request.Request(url + params, headers={"Authorization": f"Bearer {token}"})
```
