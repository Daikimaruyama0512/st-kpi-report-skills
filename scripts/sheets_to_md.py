# 必要: pip install google-auth google-auth-oauthlib
# Google Spreadsheetの内容を読み取り、Markdown形式でknowledgeフォルダに保存する
import sys, io, os, json, re, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
KNOWLEDGE_DIR = r"/Users/119322/claude-code-template_af/knowledge"

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token

# 変換対象スプレッドシート定義
TARGETS = [
    {
        "sheet_id": "18Y7A7HJWwOguajbKLS65nxPfJUcxTCDX-_TCiZvJVvs",
        "gid": 1872483588,
        "start_range": "A1",
    },
    {
        "sheet_id": "1QWJsnc-JKn-1fcjZMUygsccZXuygt4e9wY71bnxuSyQ",
        "gid": 657748746,
        "start_range": "A1",
    },
]


def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))


def get_spreadsheet_meta(sheet_id):
    """スプレッドシートのタイトルとシートタブ一覧を取得"""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=properties.title,sheets.properties"
    data = api_get(url)
    title = data.get('properties', {}).get('title', sheet_id)
    tabs = [s['properties'] for s in data.get('sheets', [])]
    return title, tabs


def get_sheet_values(sheet_id, tab_name, start_range="A1"):
    """指定タブの全データを取得"""
    range_str = f"'{tab_name}'!{start_range}:ZZZ"
    encoded_range = urllib.parse.quote(range_str)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{encoded_range}"
    data = api_get(url)
    return data.get('values', [])


def slugify(text):
    """ファイル名に使える文字列に変換"""
    text = text.strip()
    text = re.sub(r'[\s/\\:*?"<>|]+', '_', text)
    text = re.sub(r'_+', '_', text)
    text = text.strip('_')
    return text


def rows_to_markdown(rows, title, tab_name):
    """行データをMarkdownテーブルに変換"""
    # 末尾の空行を除去
    while rows and all(cell == '' for cell in rows[-1]):
        rows.pop()

    if not rows:
        return f"# {title} - {tab_name}\n\nデータなし\n"

    lines = [f"# {title} - {tab_name}", ""]

    # 最大列数を揃える
    max_cols = max(len(row) for row in rows)

    def normalize_row(row):
        padded = list(row) + [''] * (max_cols - len(row))
        return [cell.replace('|', '\\|').replace('\n', ' ') for cell in padded]

    header = normalize_row(rows[0])
    separator = ['---'] * max_cols

    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('| ' + ' | '.join(separator) + ' |')

    for row in rows[1:]:
        # 全列が空の行はスキップ
        if all(cell == '' for cell in row):
            continue
        lines.append('| ' + ' | '.join(normalize_row(row)) + ' |')

    lines.append('')
    return '\n'.join(lines)


def process_target(target):
    sheet_id = target['sheet_id']
    gid = target['gid']
    start_range = target.get('start_range', 'A1')

    print(f"\n処理中: {sheet_id} (gid={gid})")

    # メタデータ取得
    spreadsheet_title, tabs = get_spreadsheet_meta(sheet_id)
    print(f"  スプレッドシート名: {spreadsheet_title}")

    # gidからタブ名を解決
    tab_name = None
    for tab in tabs:
        if tab.get('sheetId') == gid:
            tab_name = tab.get('title', f'Sheet_{gid}')
            break
    if tab_name is None:
        tab_name = tabs[0]['title'] if tabs else 'Sheet1'
        print(f"  警告: gid={gid} のタブが見つからないため最初のタブを使用: {tab_name}")
    else:
        print(f"  タブ名: {tab_name}")

    # データ取得
    rows = get_sheet_values(sheet_id, tab_name, start_range)
    print(f"  取得行数: {len(rows)}")

    # Markdown変換
    md_content = rows_to_markdown(rows, spreadsheet_title, tab_name)

    # ファイル名決定
    filename = slugify(f"{spreadsheet_title}_{tab_name}") + ".md"
    filepath = os.path.join(KNOWLEDGE_DIR, filename)

    # 保存
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"  保存完了: knowledge/{filename}")
    return filepath


# メイン処理
print("=" * 60)
print("Sheets → Markdown 変換")
print("=" * 60)

saved_files = []
for target in TARGETS:
    try:
        path = process_target(target)
        saved_files.append(path)
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print(f"完了: {len(saved_files)} ファイル保存")
for f in saved_files:
    print(f"  - {f}")
print("=" * 60)
