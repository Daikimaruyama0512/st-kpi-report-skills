---
name: web-autopilot
description: "「〇〇のページを開いて」「スクリーンショット撮って」「フォームを自動入力して」「ページのデータを取得して」など、ブラウザ操作・Web自動化を依頼されたときに発動。Playwright（A方式）で動作する。"
allowed-tools: "Bash,Read,Write,Edit,Glob"
---

## 概要

Playwright（Chromium）を使ってブラウザを自動操作するスキル。
**A方式（Playwright）**: JavaScript・Cookie・認証付きページにも対応する本格ブラウザ自動化。

---

## 実装パターン一覧

依頼内容に応じて以下のパターンを選択してスクリプトを生成・実行する。

### パターン①: スクリーンショット撮影

```python
# 必要: pip install playwright && python -m playwright install chromium
from playwright.sync_api import sync_playwright

def screenshot(url: str, output_path: str = "screenshot.png", wait_ms: int = 2000):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    print(f"保存: {output_path}")

screenshot("https://example.com", "scripts/data/screenshot.png")
```

### パターン②: テキスト・データ抽出

```python
from playwright.sync_api import sync_playwright

def extract_text(url: str, selector: str = "body"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        elements = page.query_selector_all(selector)
        texts = [el.inner_text().strip() for el in elements if el.inner_text().strip()]
        browser.close()
    return texts

results = extract_text("https://example.com", "h2, p")
for t in results:
    print(t)
```

### パターン③: フォーム自動入力・送信

```python
from playwright.sync_api import sync_playwright

def fill_and_submit(url: str, fields: dict, submit_selector: str):
    """
    fields: {"セレクタ": "入力値", ...}
    例: {"#email": "test@example.com", "#name": "山田太郎"}
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False で操作確認可能
        page = browser.new_page()
        page.goto(url)
        for selector, value in fields.items():
            page.fill(selector, value)
        page.click(submit_selector)
        page.wait_for_load_state("networkidle")
        print("送信完了:", page.url)
        browser.close()
```

### パターン④: ログイン後ページのスクレイピング（Cookie保存）

```python
import json
from playwright.sync_api import sync_playwright
from pathlib import Path

COOKIE_FILE = "scripts/data/cookies.json"

def login_and_save_cookies(login_url: str, email: str, password: str,
                             email_sel: str, pass_sel: str, submit_sel: str):
    """初回ログインしてCookieを保存（2回目以降は不要）"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(login_url)
        page.fill(email_sel, email)
        page.fill(pass_sel, password)
        page.click(submit_sel)
        page.wait_for_load_state("networkidle")
        cookies = page.context.cookies()
        Path(COOKIE_FILE).write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
        print(f"Cookie保存: {COOKIE_FILE}")
        browser.close()

def scrape_with_cookies(url: str, selector: str):
    """保存済みCookieを使って認証済みページにアクセス"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        if Path(COOKIE_FILE).exists():
            cookies = json.loads(Path(COOKIE_FILE).read_text())
            context.add_cookies(cookies)
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        data = [el.inner_text() for el in page.query_selector_all(selector)]
        browser.close()
    return data
```

### パターン⑤: テーブルデータをCSVに変換

```python
import csv
from playwright.sync_api import sync_playwright

def table_to_csv(url: str, table_selector: str, output_csv: str = "scripts/data/table.csv"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        rows = page.query_selector_all(f"{table_selector} tr")
        data = []
        for row in rows:
            cells = row.query_selector_all("th, td")
            data.append([c.inner_text().strip() for c in cells])
        browser.close()
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(data)
    print(f"CSVに保存: {output_csv} ({len(data)}行)")
```

---

## 実行方法

ユーザーから依頼を受けたら:

1. **要件を確認**: 対象URL、操作内容（スクリーンショット/スクレイプ/フォーム入力）、出力形式
2. **パターンを選択**: 上記①〜⑤から最適なパターンを選ぶ
3. **スクリプトを生成**: `scripts/analysis/` または `scripts/data/` 配下にPythonファイルを作成
4. **実行**: `python scripts/analysis/xxx.py` で実行
5. **結果を報告**: 出力ファイルのパスと取得内容のサマリーを返す

---

## 注意事項

| 項目 | ルール |
|---|---|
| headless設定 | デフォルトは `True`。操作を目視確認したい場合は `False` に変更 |
| 待機時間 | ページ読み込み後 `wait_for_timeout(2000)` を入れると安定する |
| 認証情報 | ログイン情報をスクリプトにハードコードしない。secrets/ または .env から読む |
| rate limit | 複数ページ連続取得時は `page.wait_for_timeout(1000)` でインターバルを入れる |
| robots.txt | 取得前に対象サイトのrobots.txtを確認。禁止されているサイトはスクレイプしない |
| CSVエンコード | Windowsで開く場合は `utf-8-sig` を使う |
| 出力先 | 画像は `scripts/data/`、CSVは `scripts/data/`、スクリプト本体は `scripts/analysis/` |

---

## 動作確認コマンド

```bash
# Playwrightのインストール確認
python -m playwright --version

# Chromiumのインストール確認
python -m playwright install chromium --dry-run

# 簡易動作テスト
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    pg.goto('https://example.com')
    print('タイトル:', pg.title())
    b.close()
"
```
