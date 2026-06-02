import sys, io, json, urllib.request, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = r"/Users/119322/claude-code-template_af/secrets/token.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

token = creds.token
SHEET_ID = "19N9E6lvaK6qKds6fw8mlPHCt-lT_IzV71L4Q8c87ZZ4"

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))

def read_tab(tab_name, range_str="A1:Z200"):
    encoded = urllib.parse.quote(f"'{tab_name}'!{range_str}")
    data = api_get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}?valueRenderOption=FORMATTED_VALUE")
    return data.get('values', [])

# ① 要約タブ
print("=" * 60)
print("【要約タブ】")
print("=" * 60)
rows = read_tab("要約", "A1:Z100")
for i, row in enumerate(rows):
    if any(str(c).strip() for c in row):
        print(f"  行{i+1}: {[str(c)[:100] for c in row]}")

# ② 口コミ分析タブ
print("\n" + "=" * 60)
print("【|▶︎口コミ分析タブ】")
print("=" * 60)
rows = read_tab("|▶︎口コミ分析", "A1:Z100")
for i, row in enumerate(rows):
    if any(str(c).strip() for c in row):
        print(f"  行{i+1}: {[str(c)[:100] for c in row]}")

# ③ 学生FBリストタブ
print("\n" + "=" * 60)
print("【学生FBリストタブ】")
print("=" * 60)
rows = read_tab("学生FBリスト", "A1:Z100")
for i, row in enumerate(rows):
    if any(str(c).strip() for c in row):
        print(f"  行{i+1}: {[str(c)[:100] for c in row]}")

# ④ あんなこといいなリストタブ
print("\n" + "=" * 60)
print("【あんなこといいなリストタブ】")
print("=" * 60)
rows = read_tab("あんなこといいなリスト", "A1:Z100")
for i, row in enumerate(rows):
    if any(str(c).strip() for c in row):
        print(f"  行{i+1}: {[str(c)[:100] for c in row]}")

# ⑤ ブランド別偏差値タブ（ヘッダー+上位20行のみ）
print("\n" + "=" * 60)
print("【ブランド別偏差値タブ（ヘッダー+上位20ブランド）】")
print("=" * 60)
rows = read_tab("ブランド別偏差値", "A1:V25")
for i, row in enumerate(rows):
    if any(str(c).strip() for c in row):
        # スコア列（奇数列）のみ抽出して見やすく表示
        print(f"  行{i+1}: {[str(c)[:60] for c in row]}")

# ⑥ タグタブ
print("\n" + "=" * 60)
print("【タグタブ（先頭50行）】")
print("=" * 60)
rows = read_tab("タグ", "A1:Z50")
for i, row in enumerate(rows):
    if any(str(c).strip() for c in row):
        print(f"  行{i+1}: {[str(c)[:100] for c in row]}")
