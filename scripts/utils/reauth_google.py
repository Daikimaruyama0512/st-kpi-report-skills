"""
Google OAuth2 再認証スクリプト
token.json を削除して新しいスコープで再認証する。
ブラウザが自動で開き、Googleアカウントでの認証を求められます。
"""
import os
import sys

# プロジェクトルートを動的に解決（scripts/ の親ディレクトリ）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(PROJECT_ROOT, 'secrets', 'token.json')
CREDS_FILE = os.path.join(PROJECT_ROOT, 'secrets', 'credentials.json')

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
    except ImportError:
        print('必要なパッケージがありません。以下を実行してください:')
        print('  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client')
        sys.exit(1)

    if not os.path.exists(CREDS_FILE):
        print(f'credentials.json が見つかりません: {CREDS_FILE}')
        sys.exit(1)

    # 既存の token.json を削除
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print('既存の token.json を削除しました')

    print('ブラウザが開きます。Googleアカウントでログインして認証を完了してください...')
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

    print(f'再認証完了: {TOKEN_FILE} を更新しました')
    print('付与されたスコープ:')
    for s in SCOPES:
        print(f'  - {s}')

if __name__ == '__main__':
    main()
