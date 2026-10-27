---
name: lp-layout
description: "「黄金比に近づけて」「配置の比率を最適化して」「余白を整えて」「LPのレイアウトを改善して」など、HTMLランディングページのpadding/marginを黄金比ベースに調整したいときに発動。デザイン（色・フォント・要素構成）は変えず、スペーシングのみを最適化する。"
allowed-tools: "Read,Edit,Glob"
---

## このスキルの流れ

1. **STEP 1**: 対象HTMLファイルを読み込み、現在のpadding/marginを把握する
2. **STEP 2**: 黄金比スケールを決定する（基準値を設定）
3. **STEP 3**: セクション種別ごとに適用ルールを当てはめる
4. **STEP 4**: Edit toolでCSSのpadding/marginのみを書き換える（デザインは一切変えない）

---

## 黄金比スケール（φ = 1.618）

基準値を `φ⁰ = 3.2vw / 24px` として以下のスケールを使う。

| スケール | モバイル (vw) | デスクトップ (px) | 用途 |
|---|---|---|---|
| φ⁻¹ | 2.0vw | 15px | 密接要素間（強調→説明、ボタン→注記、数値→ラベル） |
| φ⁰  | 3.2vw | 24px | 標準間隔（タイトル→コンテンツ、アイテム内padding、リスト gap） |
| φ¹  | 5.2vw | 39px | セクション上下padding、CTA直前の呼吸 |
| φ²  | 8.4vw | 63px | 最重要セクション（ラストCTA等）の上下padding |

デスクトップ換算: `vw × 750 / 100` で近似値を出す。

---

## セクション別 適用ルール

### 通常コンテンツセクション（白・薄色背景）
```
padding: 5.2vw 横 5.2vw   (φ¹ 上下)
タイトル margin-bottom: 3.2vw  (φ⁰)
リスト gap: 3.2vw           (φ⁰)
アイテム padding: 3.2vw 横  (φ⁰)
強調→説明 margin-bottom: 1.0vw (φ⁻¹の半分、密に)
```

### head+area分離型セクション（タイトルと内容が別divの場合）
```
.head padding: 5.2vw 横 3.2vw   (上φ¹ / 下φ⁰)
.area padding: 5.2vw 横 〇vw
```

### CTAを含むセクション
```
サブコピー margin-bottom: 5.2vw  (φ¹ — CTA直前は最大間隔)
ボタン後の注記 margin-top: 2.0vw (φ⁻¹)
```

### ラストCTA（最下部の強調セクション）
```
padding: 8.4vw 横 8.4vw  (φ² — 最大余白で存在感を強調)
タイトル margin-bottom: 2.0vw   (φ⁻¹)
サブ margin-bottom: 5.2vw        (φ¹ — CTA前)
ボタン後注記 margin-top: 2.0vw  (φ⁻¹)
```

### FV（ファーストビュー）
```
padding-top: 5.2vw   (φ¹)
バッジ→コピー: 2.0vw  (φ⁻¹)
コピー→サブ: 3.2vw   (φ⁰)
サブ→CTA: 5.2vw      (φ¹ — 最重要アクションへの視線誘導)
CTA→注記: 2.0vw      (φ⁻¹)
注記→画像: 3.2vw      (φ⁰)
```

### フッター
```
padding: 5.2vw 横 5.2vw  (φ¹ — スケール統一)
```

---

## 実装ルール

- **変更対象**: `padding`・`margin`・`gap` のみ
- **変更禁止**: `color`・`font-size`・`font-weight`・`border-radius`・`background`・要素構成・HTML構造
- **vw値の丸め**: 小数第1位まで（例: 5.2vw、3.2vw）
- **デスクトップ `@media (min-width: 751px)` も必ず更新**する
- コメントで `/* φ¹ */` 等スケール名を付記して意図を残す

---

## 適用例（line_meta_IG.html より）

```css
/* FV */
.fv { padding: 5.2vw 2.6vw 0; }               /* φ¹ 上 */
.fv__copy { margin-bottom: 3.2vw; }            /* φ⁰ */
.fv__sub  { margin-bottom: 5.2vw; }            /* φ¹: CTA前 */
.fv__note { margin-top: 2.0vw; margin-bottom: 2.0vw; }  /* φ⁻¹ */
.fv__img  { margin-top: 3.2vw; }               /* φ⁰ */

/* 通常セクション */
.steps { padding: 5.2vw 2.6vw 5.2vw; }        /* φ¹ */
.steps .section__ttl { margin-bottom: 3.2vw; } /* φ⁰ */
.steps__list { margin-bottom: 5.2vw; }         /* φ¹: リスト→CTA */

/* ラストCTA */
.last_cta { padding: 8.4vw 2.6vw 8.4vw; }     /* φ² */
.last_cta__sub { margin-bottom: 5.2vw; }       /* φ¹: CTA前 */
```

---

## 判断基準

| 間隔の性質 | 使うスケール |
|---|---|
| 同一情報グループ内（強調テキスト→説明テキスト） | φ⁻¹ (2.0vw) |
| 異なる情報ブロック間（タイトル→本文、アイテム間） | φ⁰ (3.2vw) |
| セクション境界、CTA直前 | φ¹ (5.2vw) |
| 最重要アクションセクションの上下余白 | φ² (8.4vw) |
