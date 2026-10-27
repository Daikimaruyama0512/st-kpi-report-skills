"""
Google SheetsとSlidesのスクリーンショットとテキストを取得する
必要: pip install playwright && python -m playwright install chromium
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHROME_PROFILE = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome"
)

URLS = [
    {
        "url": "https://docs.google.com/spreadsheets/d/1UakK5ig5spCTQmgdrd32XsJjiHLyAmGhymb1B5o-i8s/edit?gid=661700305#gid=661700305",
        "out_img": os.path.join(OUTPUT_DIR, "compare_sheet.png"),
        "label": "スプレッドシート",
    },
    {
        "url": "https://docs.google.com/presentation/d/1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0/edit?slide=id.slide13#slide=id.slide13",
        "out_img": os.path.join(OUTPUT_DIR, "compare_slide13.png"),
        "label": "スライド13枚目",
    },
]


def fetch_page(page, url_info):
    print(f"\n--- {url_info['label']} ---")
    page.goto(url_info["url"], wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(4000)

    # スクリーンショット
    page.screenshot(path=url_info["out_img"], full_page=False)
    print(f"スクリーンショット保存: {url_info['out_img']}")

    # テキスト取得
    text = page.inner_text("body")
    return text


def main():
    with sync_playwright() as p:
        # Chromeプロファイルを使って認証済みセッションを利用
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE,
                headless=True,
                channel="chrome",
                args=["--disable-extensions"],
                viewport={"width": 1600, "height": 900},
            )
            page = browser.new_page()
        except Exception as e:
            print(f"Chromeプロファイル読み込み失敗: {e}")
            print("通常のChromiumで再試行します...")
            browser2 = p.chromium.launch(headless=False)
            page = browser2.new_page(viewport={"width": 1600, "height": 900})

        texts = {}
        for url_info in URLS:
            try:
                text = fetch_page(page, url_info)
                texts[url_info["label"]] = text
            except Exception as e:
                print(f"エラー ({url_info['label']}): {e}")
                texts[url_info["label"]] = ""

        browser.close()

    # テキストをファイルに保存
    for label, text in texts.items():
        safe_label = label.replace("/", "_")
        out_txt = os.path.join(OUTPUT_DIR, f"compare_{safe_label}.txt")
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"テキスト保存: {out_txt}")
        # 先頭500文字を表示
        preview = text[:500].replace("\n", " / ")
        print(f"プレビュー: {preview}...")


if __name__ == "__main__":
    main()
