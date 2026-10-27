"""
直接競合5社のFVスクリーンショット撮影 + テキスト抽出
必要: pip install playwright && python -m playwright install chromium
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/Users/119322/Desktop/claude-code-template_af/scripts/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 390, "height": 844}
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

COMPETITORS = [
    ("jukunavi",  "https://jukunavi.com/"),
    ("jukukoushi_jp", "https://www.jukukoushi.jp/"),
    ("jukuwork",  "https://www.jukuwork.com/"),
    ("try_invite", "https://www.trygroup.co.jp/invite/"),
    ("succeed",   "https://www.succeed-jinzai.jp/jukukoushi/"),
]


def analyze_page(page):
    """h1・主要コピー・CTAボタンを抽出"""
    result = {}
    # h1
    h1 = page.query_selector("h1")
    result["h1"] = h1.inner_text().strip() if h1 else ""
    # 全ボタン/aタグのテキスト（FV付近）
    btns = page.query_selector_all("a, button")
    btn_texts = []
    for b in btns[:20]:
        t = b.inner_text().strip()
        if t and len(t) < 60:
            btn_texts.append(t)
    result["cta_candidates"] = btn_texts
    # title
    result["title"] = page.title()
    # meta description
    desc = page.query_selector('meta[name="description"]')
    result["description"] = desc.get_attribute("content") if desc else ""
    return result


def capture(slug, url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,
            user_agent=UA,
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=20000)
        except Exception:
            page.wait_for_timeout(3000)

        page.wait_for_timeout(2500)

        # FVクリップ
        img_path = str(OUTPUT_DIR / f"fv_{slug}.png")
        page.screenshot(
            path=img_path,
            clip={"x": 0, "y": 0, "width": 390, "height": 844},
        )

        # テキスト情報抽出
        info = analyze_page(page)
        info["url"] = page.url
        browser.close()

    json_path = str(OUTPUT_DIR / f"fv_{slug}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"[{slug}] 保存: {img_path}")
    print(f"  title: {info['title'][:60]}")
    print(f"  h1: {info['h1'][:60]}")
    print(f"  CTA候補: {info['cta_candidates'][:5]}")
    return info


if __name__ == "__main__":
    for slug, url in COMPETITORS:
        print(f"\n--- {slug} ---")
        try:
            capture(slug, url)
        except Exception as e:
            print(f"  ERROR: {e}")
    print("\n完了。scripts/data/ にPNG・JSONを保存しました。")
