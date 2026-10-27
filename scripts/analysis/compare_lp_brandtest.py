# LP比較スクリーンショット + テキスト抽出
# 必要: pip install playwright && python -m playwright install chromium

from playwright.sync_api import sync_playwright
import json

PAGES = [
    {"name": "LP-A_旧", "url": "https://sb2.juku.st/brandtest"},
    {"name": "LP-B_新", "url": "https://sb2.juku.st/brandtest_m2"},
]
VIEWPORT = {"width": 390, "height": 844}  # iPhone14 サイズ

def capture(page_info):
    name = page_info["name"]
    url  = page_info["url"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # FV（viewport分のみ）
        fv_path = f"scripts/data/lp_{name}_fv.png"
        page.screenshot(path=fv_path, full_page=False)

        # フルページ
        full_path = f"scripts/data/lp_{name}_full.png"
        page.screenshot(path=full_path, full_page=True)

        # テキスト抽出
        texts = page.evaluate("""() => {
            const walk = (el, depth) => {
                const tag = el.tagName ? el.tagName.toLowerCase() : '';
                const skip = ['script','style','noscript','svg','head'];
                if (skip.includes(tag)) return [];
                const text = (el.innerText || '').trim();
                if (el.children && el.children.length === 0 && text) {
                    return [{tag, text, depth}];
                }
                let results = [];
                for (const child of (el.children || [])) {
                    results = results.concat(walk(child, depth+1));
                }
                return results;
            };
            return walk(document.body, 0);
        }""")
        # 重複除去・空行除去
        seen = set()
        lines = []
        for t in texts:
            txt = t['text'].strip()
            if txt and txt not in seen:
                seen.add(txt)
                lines.append(f"[{t['tag']}] {txt}")

        browser.close()
        return {"name": name, "url": url, "fv": fv_path, "full": full_path, "texts": lines}

results = {}
for pg in PAGES:
    print(f"取得中: {pg['name']} ({pg['url']})")
    r = capture(pg)
    results[pg["name"]] = r
    print(f"  FV: {r['fv']}")
    print(f"  Full: {r['full']}")
    print(f"  テキスト {len(r['texts'])} 件")

# テキストをJSONで保存
with open("scripts/data/lp_compare_texts.json", "w", encoding="utf-8") as f:
    json.dump({k: v["texts"] for k, v in results.items()}, f, ensure_ascii=False, indent=2)

print("\n=== LP-A テキスト ===")
for t in results["LP-A_旧"]["texts"]:
    print(t)

print("\n=== LP-B テキスト ===")
for t in results["LP-B_新"]["texts"]:
    print(t)
