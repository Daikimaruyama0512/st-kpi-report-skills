# スプレッドシート → JSON エクスポートスクリプト
# 必要: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

import json
import sys
import io
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN_FILE  = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

SPREADSHEET_ID  = "1_9Hkt2s19i88wDs1ioZvuEb2Iligd8kr25XxAluvYFM"
MEMBER_SHEET    = "自己紹介スクリプト"
TWEET_SHEET     = "つぶやき"

OUTPUT_DIR = Path("/Users/119322/Desktop/claude-code-template_af/scripts/data")
MEMBERS_JSON = OUTPUT_DIR / "members_export.json"
TWEETS_JSON  = OUTPUT_DIR / "tweets_export.json"


def get_credentials():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return creds


def fetch_sheet(service, sheet_name):
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_name
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return []
    headers = rows[0]
    records = []
    for row in rows[1:]:
        # 列数が足りない場合は空文字で補完
        padded = row + [""] * (len(headers) - len(row))
        record = {headers[i]: padded[i] for i in range(len(headers))}
        records.append(record)
    return records


def main():
    print("Google Sheets API に接続中...")
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    print(f"シート「{MEMBER_SHEET}」を取得中...")
    members = fetch_sheet(service, MEMBER_SHEET)
    print(f"  → {len(members)} 件のメンバーデータを取得")

    print(f"シート「{TWEET_SHEET}」を取得中...")
    tweets = fetch_sheet(service, TWEET_SHEET)
    print(f"  → {len(tweets)} 件のつぶやきを取得")

    # 列名確認（最初の1件を表示）
    if members:
        print("\nメンバーシートのカラム名:")
        print("  " + ", ".join(members[0].keys()))
        print("最初のレコード（サンプル）:")
        for k, v in members[0].items():
            print(f"  {k}: {v[:40] if v else ''}")

    if tweets:
        print("\nつぶやきシートのカラム名:")
        print("  " + ", ".join(tweets[0].keys()))

    # JSON出力
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(MEMBERS_JSON, "w", encoding="utf-8") as f:
        json.dump(members, f, ensure_ascii=False, indent=2)
    print(f"\n保存完了: {MEMBERS_JSON}")

    with open(TWEETS_JSON, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"保存完了: {TWEETS_JSON}")

    print("\nエクスポート完了。")


if __name__ == "__main__":
    main()
