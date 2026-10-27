# Google Slides メンバー名取得スクリプト
# Drive API export（text/plain）でプレゼン全文取得
# 必要: pip install google-api-python-client google-auth

import sys
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN_FILE = r"/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

PRESENTATION_ID = "1bKzAvqg0u7xVqFsUo9FiNKLm0FGZk2JfYV47tHd4cMA"


def main():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    drive = build("drive", "v3", credentials=creds)

    print("Drive API でプレゼンテーションをエクスポート中...")
    content = drive.files().export(
        fileId=PRESENTATION_ID,
        mimeType="text/plain"
    ).execute()

    text = content.decode("utf-8")

    # 全文を出力
    print("\n===== プレゼンテーション全文 =====")
    print(text)
    print("===== 全文終了 =====")
    print(f"\n総文字数: {len(text)}")

    # テキストをファイルにも保存
    output_path = "/Users/119322/Desktop/claude-code-template_af/scripts/data/slides_text.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"テキストを保存: {output_path}")


if __name__ == "__main__":
    main()
