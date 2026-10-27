---
name: lp-create
description: "「LPを作って」「ランディングページを作って」「競合を参考にLPを作りたい」「新しいLPを作って」など、ランディングページをゼロから作成したいときに発動。競合スクショ → 分析 → 構成設計 → HTML生成 → プレビュー確認まで一貫して行う。"
allowed-tools: "Bash,Read,Write,Edit,Glob"
---

## このスキルの流れ

1. **STEP 1**: ヒアリング（URL・用途・FV方式）
2. **STEP 2**: 自社・競合LPをスクリーンショット取得
3. **STEP 3**: スクショを読んでデザイン分析
4. **STEP 4**: knowledgeファイルを読み込む
5. **STEP 5**: セクション構成を設計 → ユーザー確認
6. **STEP 6**: FV生成（分岐A: HTML / 分岐B: Canva）
7. **STEP 7**: LP全体のHTML生成
8. **STEP 8**: Playwrightでプレビュー確認
9. **STEP 9**: 修正ループ

---

## STEP 1: ヒアリング

以下が未指定の場合はユーザーに聞く。

| 項目 | 内容 |
|---|---|
| 自社参照LP URL | 既存LPのURL（デザイン・コンテンツの参照元） |
| 競合URL | 最大3つ（なければスキップ） |
| LP用途 | Meta広告流入 / Google広告流入 / SNS / その他 |
| FV生成方式 | **A = HTMLコーディング** / **B = Canva生成**（後でiframe埋め込み） |
| 出力ファイル名 | 例: `lp/new_lp.html`（デフォルト: `lp/lp_YYYYMMDD.html`） |

---

## STEP 2: スクリーンショット取得

web-autopilot スキルのパターン①を使って各URLをスクリーンショットする。

```python
# 必要: pip install playwright && python -m playwright install chromium
from playwright.sync_api import sync_playwright

def screenshot(url: str, output_path: str, wait_ms: int = 3000):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})  # モバイルビュー
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    print(f"保存: {output_path}")
```

保存先:
- 自社LP: `scripts/data/lp_ref_own.png`
- 競合1: `scripts/data/lp_ref_comp1.png`
- 競合2: `scripts/data/lp_ref_comp2.png`
- 競合3: `scripts/data/lp_ref_comp3.png`

スクリプトは `scripts/analysis/screenshot_lp_refs.py` として保存して実行する。

---

## STEP 3: スクショ分析

取得した画像を Read tool で読み込んで以下の項目を抽出する。

```
【分析テンプレ】
■ カラーパレット
  - メインカラー: #______
  - アクセント: #______
  - 背景: #______

■ セクション構成（上から順に）
  1. FV: [キャッチコピー / CTA / 画像の有無]
  2. 実績数値: [項目数 / 配置]
  3. ...

■ CTAの特徴
  - 文言: 「〇〇」
  - 位置: FV内 / 各セクション末 / 固定フッター
  - カラー: #______

■ 画像・写真の使い方
  - FVに人物写真あり/なし
  - イラスト多め / 写真多め
  - 比率（横:縦）

■ キャッチコピーの構造
  - 訴求軸: [課題解決型 / ベネフィット型 / 数字型]
  - 例: 「〇〇〇〇〇〇〇〇」
```

分析結果をチャットに出力し、競合との差分・参考にすべきポイントをまとめる。

---

## STEP 4: knowledgeファイル読み込み

以下を**すべて**読んでからLP設計を始める。

| ファイル | 読み取る情報 |
|---|---|
| `knowledge/business/business-overview.md` | 事業概要・KPI・訴求軸 |
| `knowledge/target/who_what_how.md` | ターゲット像・インサイト・ペインポイント |
| `knowledge/target/customer_info.md` | 詳細な顧客情報（あれば） |

---

## STEP 5: セクション構成設計 → ユーザー確認

以下のテンプレを元に構成案を提示し、**ユーザーの確認を得てから次へ進む**。

```
【LP構成案】

1. FV（ファーストビュー）
   - キャッチ: 「〇〇〇〇〇〇〇〇」
   - サブコピー: 〇〇〇〇〇〇
   - CTA: 「〇〇〇〇」（LINE緑 or オレンジ）
   [画像プレースホルダー: 塾講師・生徒の写真 / 推奨比率 16:9 / 代替: #F5F0EB クリーム背景]
   ※ FV方式: A=HTML / B=Canva

2. 実績数値（STATS）
   - 〇〇万件 / 〇万人 / 〇秒 など3〜4項目

3. 3ステップ
   - LINE登録 → 診断 → 応募
   [画像プレースホルダー: 各ステップのアイコン画像 / 推奨: 正方形]

4. 口コミ・体験談
   [画像プレースホルダー: 口コミカード画像 / 推奨比率 3:2]

5. 〇〇が選ばれる理由
   - 4〜5項目リスト

6. ラストCTA
   - 「〇〇〇〇〇〇」（フルオレンジ背景）
```

---

## STEP 6: FV生成（分岐）

### 分岐A: HTML コーディング

FVのHTML/CSSをコーディングして `lp-layout` スキルの黄金比スペーシングを適用する。

```css
/* FV スペーシング（黄金比 φ¹=5.2vw / φ⁰=3.2vw / φ⁻¹=2.0vw） */
.fv { padding: 5.2vw 2.6vw 0; }
.fv__copy { margin-bottom: 3.2vw; }    /* φ⁰ */
.fv__sub  { margin-bottom: 5.2vw; }    /* φ¹: CTA前 */
.fv__note { margin-top: 2.0vw; }       /* φ⁻¹ */
.fv__img  { margin-top: 3.2vw; }       /* φ⁰ */
```

画像エリアは以下のプレースホルダーで実装:
```html
<!-- [画像プレースホルダー: 〇〇の写真 / 推奨比率: 16:9] -->
<div class="fv__img_placeholder" style="
  width: 100%;
  aspect-ratio: 16/9;
  background: #F5F0EB;
  border-radius: 3.2vw;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aaa;
  font-size: 3.2vw;
">📷 塾講師・生徒の写真（16:9）</div>
```

### 分岐B: Canva 生成（FVのみ）

canva-story-design スキルを参照してFVをCanva上で生成する。

**Canva FV生成の手順:**
1. `search-designs` で既存の近いデザインを検索（"ストーリー" で検索）
2. `read-design` でデザインを開いてトランザクション取得
3. LP準拠の2分割レイアウトを適用:
   - 上部（Y:0〜1000）: クリーム `#F5F0EB`（画像配置スペース）
   - 下部（Y:1000〜1920）: オレンジ `#FF7019`（テキストエリア）
4. テキストを配置:
   - キャッチコピー: top=1020, color=#ffffff
   - サブコピー: top=1560, color=#ffe0cc
   - CTA文言: top=1810, color=#ffffff
5. `finalize: commit` でコミット
6. CanvaのデザインURLから embedコードを取得してHTMLに組み込む:

```html
<!-- Canva FV embed -->
<div class="fv__canva" style="position:relative;width:100%;padding-top:177.78%;overflow:hidden;">
  <iframe
    style="position:absolute;top:0;left:0;width:100%;height:100%;border:none;"
    src="https://www.canva.com/design/[DESIGN_ID]/view?embed"
    allowfullscreen>
  </iframe>
</div>
```

7. FV以外のセクションは通常通りHTMLでコーディング

---

## STEP 7: LP全体のHTML生成

STEP5の構成・STEP6のFVを元にLP全体のHTMLを生成する。

**適用するスタイル標準:**
- フォント: M PLUS Rounded 1c（Google Fonts）
- ブランドカラー: `#FF7019`（オレンジ）/ `#06C755`（LINE緑）/ `#FAE2D1`（背景）
- 最大幅: `max-width: 750px`（モバイルファースト）
- スペーシング: lp-layoutスキルの黄金比スケールを全セクションに適用

**画像プレースホルダーの書き方:**
```html
<!-- [画像プレースホルダー: 〇〇の写真 / 推奨比率: 〇:〇 / ファイル名例: img_section.jpg] -->
<div class="img_placeholder" style="
  aspect-ratio: 〇/〇;
  background: #F5F0EB;
  border-radius: 2.6vw;
  display: flex; align-items: center; justify-content: center;
  color: #bbb; font-size: 3vw;
">📷 〇〇の写真</div>
```

保存先: `lp/` フォルダ（ファイル名はSTEP1で確認した名前）

---

## STEP 8: Playwright プレビュー確認

以下のスクリプトで生成したLPをスクリーンショットして目視確認する。

```python
# scripts/analysis/screenshot_lp.py
from playwright.sync_api import sync_playwright
import os

def screenshot_local(file_path: str, output_path: str):
    abs_path = os.path.abspath(file_path)
    url = f"file://{abs_path}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    print(f"保存: {output_path}")

screenshot_local("lp/new_lp.html", "scripts/data/lp_preview.png")
```

確認チェックリスト:
- [ ] FVのキャッチ・CTA・画像プレースホルダーが正しく配置されているか
- [ ] 各セクションが重なっていないか
- [ ] ブランドカラーが正しく適用されているか
- [ ] 画像プレースホルダーの比率が正しいか
- [ ] モバイル幅(390px)でレイアウト崩れがないか

---

## STEP 9: 修正ループ

ユーザーのフィードバックに応じて修正する。

- **テキスト修正** → STEP7の該当箇所をEditで修正 → STEP8で再確認
- **構成の大幅変更** → STEP5に戻る
- **Canva FVの調整** → canva-story-designスキルを参照

---

## 注意事項

| 項目 | ルール |
|---|---|
| 画像素材 | 実ファイルは用意しない。プレースホルダー（クリーム背景＋テキスト）で配置を示す |
| 画像プレースホルダー | コメントに「推奨比率」「用途説明」を必ず記載する |
| Canva FV | embed URLは `view?embed` 形式で取得する（公開設定が必要） |
| robots | LPには `<meta name="robots" content="noindex,nofollow">` を付与する |
| GTM | `knowledge/business/business-overview.md` にGTM-IDが記載されていれば挿入する |
| ファイル保存先 | `lp/` フォルダに保存（なければ作成） |
