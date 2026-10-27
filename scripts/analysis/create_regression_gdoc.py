# 広告費 × CVR/CPA 回帰分析レポート → Google Document 新規作成
# 必要: pip install google-auth google-auth-oauthlib

import sys, io, os, json, urllib.request, urllib.error
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]
TOKEN_FILE = '/Users/119322/Desktop/claude-code-template_af/secrets/token.json'
CREDS_FILE = '/Users/119322/Desktop/claude-code-template_af/secrets/credentials.json'

# ── 認証 ─────────────────────────────────────────────────
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())
token = creds.token

def api(url, body=None, method=None):
    data = json.dumps(body).encode('utf-8') if body else None
    m = method or ('POST' if data else 'GET')
    req = urllib.request.Request(
        url, data=data,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method=m,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f'HTTP Error {e.code}: {e.read().decode()}')
        raise

# ── ドキュメント作成 ──────────────────────────────────────
title = '広告費 × CVR/CPA 回帰分析レポート（訴求軸別）'
doc = api('https://docs.googleapis.com/v1/documents', {'title': title})
doc_id = doc['documentId']
print(f'ドキュメント作成: {doc_id}')

# ── テキストブロック定義（最終的な出現順） ─────────────────
# style: 'h1' | 'h2' | 'body' | 'table_here'
# table_here はテーブル挿入位置のプレースホルダー（\n 1文字）

text_blocks = [
    ('h1',         'データ概要\n'),
    ('body',       'CA: 405広告 / ST: 117広告 / 合計: 522広告（spend ≥ 1万円）\n'
                   'CA・STを合算。新命名規則（訴求軸抽出可能）: 186本 / OTHER（旧命名規則）: 336本\n'
                   '分析条件: spend ≥ 10,000円・CV > 0・link_clicks > 0\n\n'),
    ('h1',         '訴求軸別 回帰サマリ\n'),
    ('table_here', '\n'),          # ← テーブルをここに挿入
    ('h1',         'インサイト\n'),
    ('body',       '【結論】\n'
                   '広告費とCVR/CPAの間に強い線形関係は全体的に見られないが、'
                   'D: 所属のCPAのみ統計的に有意（p=0.010）。'
                   'E: 潜在層はCPAが最も低く（12,680円）、スケール余地も示唆される。\n\n'),
    ('h2',         '訴求軸別 解説\n'),
    ('body',       'E: 潜在層（n=54）\n'
                   'CPA平均12,680円と最良。CPA回帰p=0.084でやや有意傾向。広告費を増やすほどCPAが下がる可能性がある。\n\n'
                   'D: 所属（n=40）\n'
                   'CPA回帰がp=0.010★で唯一有意。R²=0.163。スケールメリットが出ている可能性。\n\n'
                   'A: 安心（n=64）\n'
                   'R²≒0、p=0.725。広告費との相関なし。CPA 18,495円と高め。クリエイティブ個体差が支配的。\n\n'
                   'F: 企業PUSH（n=24）\n'
                   'CVR 2.02%と低め。広告費との相関も弱い。\n\n'
                   'G: 潜在層_3分診断（n=3）\n'
                   'CVR 9.29%・CPA 7,304円と突出した効率だがサンプル不足のため回帰不可。\n\n'),
    ('h2',         '推奨アクション\n'),
    ('body',       '① E: 潜在層 の予算増額を検討\n'
                   'CPA最良＋スケール効果の傾向あり\n\n'
                   '② G: 潜在層_3分診断 を増産\n'
                   '効率は最高水準。10本以上出稿して再回帰で検証\n\n'
                   '③ A: 安心 は予算固定\n'
                   'スケールしても改善しない。クリエイティブ単体の質勝負\n'),
]

# ── 各ブロックの最終位置を計算 ────────────────────────────
# ドキュメント作成直後: index 1 に \n が1文字ある
# index 1 に逆順で挿入するとブロックの順が正しくなる
positions = []
idx = 1
for style, text in text_blocks:
    positions.append((style, text, idx, idx + len(text)))
    idx += len(text)

table_placeholder = next(p for p in positions if p[0] == 'table_here')
table_insert_idx = table_placeholder[2]  # \n の位置

# ── テキストを逆順で index=1 に挿入 ──────────────────────
print('テキスト挿入中...')
for style, text, start, end in reversed(positions):
    api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate', {
        'requests': [{'insertText': {'location': {'index': 1}, 'text': text}}]
    })

# ── 見出し書式を一括適用（50件以下なのでまとめて送信） ─────
print('見出し書式適用中...')
format_requests = []
for style, text, start, end in positions:
    if style in ('h1', 'h2'):
        named = 'HEADING_1' if style == 'h1' else 'HEADING_2'
        format_requests.append({
            'updateParagraphStyle': {
                'range': {'startIndex': start, 'endIndex': end},
                'paragraphStyle': {'namedStyleType': named},
                'fields': 'namedStyleType',
            }
        })

api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
    {'requests': format_requests})

# ── テーブル挿入 ──────────────────────────────────────────
print('テーブル挿入中...')
TABLE_ROWS = [
    ['訴求軸', 'n', 'CVR平均', 'CPA平均', 'CVR R²', 'CVR p', 'CPA R²', 'CPA p'],
    ['E: 潜在層',        '54', '4.18%',  '12,680円',  '0.009', '0.506',   '0.056', '0.084'],
    ['A: 安心',          '64', '3.87%',  '18,495円',  '0.002', '0.725',   '0.006', '0.545'],
    ['D: 所属',          '40', '3.06%',  '16,975円',  '0.020', '0.389',   '0.163', '0.010★'],
    ['F: 企業PUSH',      '24', '2.02%',  '15,144円',  '0.028', '0.433',   '0.062', '0.239'],
    ['G: 潜在層_3分診断', '3', '9.29%',  '7,304円',   '—',     '(n=3)',   '—',     '(n=3)'],
]

api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate', {
    'requests': [{
        'insertTable': {
            'rows': len(TABLE_ROWS),
            'columns': len(TABLE_ROWS[0]),
            'location': {'index': table_insert_idx},
        }
    }]
})

# ── ドキュメントを再取得してテーブルセル位置を特定 ──────────
print('テーブルセル位置を取得中...')
doc_data = api(f'https://docs.googleapis.com/v1/documents/{doc_id}')

def find_table_cells(content):
    """ドキュメントcontent から tableCell の startIndex を行×列の順で返す"""
    cells = []
    for elem in content:
        if 'table' in elem:
            for row in elem['table']['tableRows']:
                row_cells = []
                for cell in row['tableCells']:
                    # cellの最初のparagraphの最初のtextRunのstartIndex
                    cell_start = cell['content'][0]['startIndex']
                    row_cells.append(cell_start)
                cells.append(row_cells)
    return cells

cell_positions = find_table_cells(doc_data['body']['content'])

if not cell_positions:
    print('テーブルが見つかりませんでした。スキップします。')
else:
    # ── セルにテキストを挿入（逆順で） ─────────────────────
    print('セルテキスト挿入中...')
    cell_requests = []
    for r_idx, row in enumerate(TABLE_ROWS):
        for c_idx, cell_text in enumerate(row):
            if r_idx < len(cell_positions) and c_idx < len(cell_positions[r_idx]):
                cell_start = cell_positions[r_idx][c_idx]
                cell_requests.append({
                    'insertText': {
                        'location': {'index': cell_start},
                        'text': cell_text,
                    }
                })

    # 逆順で挿入（インデックスがずれないように後ろから）
    cell_requests_sorted = sorted(cell_requests,
        key=lambda x: x['insertText']['location']['index'], reverse=True)

    # 50件ずつ送信
    for i in range(0, len(cell_requests_sorted), 50):
        batch = cell_requests_sorted[i:i+50]
        api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
            {'requests': batch})

    # ── ヘッダー行に背景色を適用 ────────────────────────────
    print('ヘッダー行の書式適用中...')
    if cell_positions:
        header_row = cell_positions[0]
        shading_requests = []
        for c_idx in range(len(header_row)):
            cell_start = header_row[c_idx]
            cell_text = TABLE_ROWS[0][c_idx]
            shading_requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': cell_start, 'endIndex': cell_start + len(cell_text)},
                    'textStyle': {'bold': True},
                    'fields': 'bold',
                }
            })
        api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
            {'requests': shading_requests})

# ── 完了・URL出力 ─────────────────────────────────────────
url = f'https://docs.google.com/document/d/{doc_id}/edit'
print(f'\n完了！')
print(f'タイトル: {title}')
print(f'URL: {url}')
