from playwright.sync_api import sync_playwright

def screenshot(url: str, output_path: str = "scripts/data/brandtest.png", wait_ms: int = 3000):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # モバイルサイズで撮影（ページがmax-width: 360pxのため）
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    print(f"保存: {output_path}")

screenshot("https://sb2.juku.st/brandtest", "scripts/data/brandtest.png")
