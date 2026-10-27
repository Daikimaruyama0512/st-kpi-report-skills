"""
FV比較用スクリーンショット撮影
- 現行: https://sb2.juku.st/brandtest
- 修正案: lp/line_meta_IG.html (ローカル)
必要: pip install playwright && python -m playwright install chromium
"""
from playwright.sync_api import sync_playwright
from pathlib import Path

OUTPUT_DIR = Path("/Users/119322/Desktop/claude-code-template_af/scripts/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# iPhone 14想定スマホビューポート
VIEWPORT = {"width": 390, "height": 844}

def screenshot_fv(url_or_path: str, output_path: str, is_local: bool = False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        )
        page = context.new_page()

        if is_local:
            page.goto(f"file://{url_or_path}", wait_until="networkidle")
        else:
            page.goto(url_or_path, wait_until="networkidle")

        page.wait_for_timeout(2500)

        # FVのみをクリップ（上部 844px = スマホ1画面分）
        page.screenshot(
            path=output_path,
            clip={"x": 0, "y": 0, "width": 390, "height": 844},
        )
        browser.close()
    print(f"保存: {output_path}")


# ① 現行ページ
screenshot_fv(
    "https://sb2.juku.st/brandtest",
    str(OUTPUT_DIR / "fv_current.png"),
)

# ② 修正案（ローカルHTML）
local_html = "/Users/119322/Desktop/claude-code-template_af/lp/line_meta_IG.html"
screenshot_fv(
    local_html,
    str(OUTPUT_DIR / "fv_modified.png"),
    is_local=True,
)

print("完了。2枚のFVスクリーンショットを保存しました。")
