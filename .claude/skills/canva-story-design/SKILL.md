---
name: canva-story-design
description: "「CanvaのStoriesを改善して」「LPに合わせてデザインを直して」「背景を差し替えて」「テキストレイアウトを整えて」など、Canva Instagram Stories/FVデザインの編集・改善を依頼されたときに発動。Canva MCP APIを使ってデザインを直接編集する。"
allowed-tools: "mcp__claude_ai_Canva__search-designs,mcp__claude_ai_Canva__read-design,mcp__claude_ai_Canva__edit-design,mcp__claude_ai_Canva__get-design-candidates,Bash,Read,Write"
---

## このスキルの流れ

1. **STEP 1**: 対象デザインを特定する（検索 or DesignID直指定）
2. **STEP 2**: デザインを読み込み・現状把握（トランザクション開始）
3. **STEP 3**: 改善内容を計画する（カラー・レイアウト・テキスト）
4. **STEP 4**: 編集を実行する（背景隠蔽 → レイアウト → テキスト）
5. **STEP 5**: サムネイルで確認してコミットする

---

## STブランドカラー（LP準拠）

| 用途 | カラーコード |
|---|---|
| メインオレンジ（CTA帯・アクセント） | `#ff7019` |
| 写真スペース背景（クリーム） | `#f5f0eb` |
| LINEグリーン（CTAボタン） | `#06c755` |
| テキスト白 | `#ffffff` |
| テキストサブ（オレンジ帯上） | `#ffe0cc` |
| テキスト濃い（クリーム帯上） | `#08161a` |

---

## STEP 1: 対象デザインの特定

DesignIDが不明な場合は `search-designs` で探す。

```
search-designs: query="ストーリー 塾講師STATION"
```

複数ある場合はデザイン名・サムネイルをユーザーに提示して確認を取る。

---

## STEP 2: 現状把握

```
read-design:
  design_id: <DESIGN_ID>
  open_transaction: true
  filter.fields: ["design_content", "thumbnails"]
  filter.page_indices: [1]
```

確認ポイント：
- キャンバスサイズ（通常1080×1920）
- 背景の種類（IMAGE / COLOR）
- テキスト要素のID・位置・色・フォントサイズ
- グループ構造（GROUP要素）
- テキストが範囲外（left/top > 1080 or 1920）に飛んでいないか

---

## STEP 3: 改善計画

### 背景に英語テンプレートテキストが焼き込まれている場合

背景画像は直接編集不可。**色付き矩形で覆う**ことで対処する。

**推奨レイアウト（2分割）**:
```
上部50% (Y:0〜1000)   → クリーム #f5f0eb（写真スペース）
下部50% (Y:1000〜1920) → オレンジ #ff7019（テキストエリア）
```

写真スペースが不要な場合は全面オレンジにする。

### テキスト重なりが発生している場合

グループ解除（`ungroup_elements`）してから位置を個別調整する。

### テキストがキャンバス外にある場合

`position_element` でキャンバス内（left=60〜, top=1020〜）に移動する。

---

## STEP 4: 編集操作パターン

### パターンA: 上部写真スペース + 下部オレンジ帯

```
操作順序（同一トランザクション内）:

1. delete_element: 既存の全面白矩形を削除（あれば）

2. insert_shape: クリーム上部矩形
   - page_id: <PAGE_ID>
   - top: 0, left: 0, width: 1080, height: 1000
   - color: #f5f0eb, opacity: 1
   - path: "M 0 0 L 1 0 L 1 1 L 0 1 Z"
   - view_box_width: 1, view_box_height: 1
   → IDを取得

3. layer_element: クリーム矩形 → back

4. insert_shape: オレンジ下部矩形
   - top: 1000, left: 0, width: 1080, height: 920
   - color: #ff7019, opacity: 1
   → IDを取得

5. layer_element: オレンジ矩形 → back

（クリームより後ろになり、上部=クリーム / 下部=オレンジの2分割が完成）

6. ungroup_elements: テキストグループがあれば解除

7. position_element: 各テキストをオレンジ帯内（top:1020〜1860）へ移動

8. format_text: テキスト色を白/クリームに変更
```

### パターンB: 全面オレンジ背景

```
1. insert_shape: オレンジ全面
   - top: 0, left: 0, width: 1080, height: 1920
   - color: #ff7019
   → IDを取得

2. layer_element: → back

3. テキスト色を白に変更
```

### テキスト標準配置（オレンジ帯内、高さ920px想定）

| テキスト | top | left | color |
|---|---|---|---|
| メインキャッチ（大） | 1020 | 60 | #ffffff |
| サブテキスト | 1560 | 60 | #ffe0cc |
| CTA（LINE登録等） | 1810 | 60 | #ffffff |

---

## STEP 5: サムネイル確認 → コミット

サムネイルで以下を確認してからコミット:
- 英語テキストが隠れているか
- テキストが重なっていないか
- 全テキストがキャンバス内に収まっているか
- オレンジ帯にテキストが正しく載っているか

```
edit-design:
  transaction_id: <TX_ID>
  finalize: "commit"
```

---

## 注意事項

| 項目 | ルール |
|---|---|
| 背景画像 | `replaceable=true` でも `update_fill` 以外での直接編集は不可。矩形で覆う方法を使う |
| レイヤー順 | documentの上から順に最背面→最前面。`layer_element back` を複数回呼ぶ場合、最後にbackにした要素が最背面になる |
| テキストの色 | オレンジ背景上でオレンジ文字は不可視。必ず白(#ffffff)か#ffe0ccに変更する |
| グループ内テキスト | position_elementはグループ解除後に行う（グループ内要素の直接移動は不安定） |
| コミットは最後に1回 | 編集操作と `finalize:commit` は別callで行う（同時実行は拒否される） |
| 確認行動 | コミット前に必ずサムネイルで目視確認する |

---

## よく使うCanva操作リファレンス

```
# 矩形挿入
insert_shape:
  type: insert_shape
  page_id: <PAGE_ID>
  top: 0, left: 0, width: 1080, height: 1920
  path: "M 0 0 L 1 0 L 1 1 L 0 1 Z"
  view_box_width: 1, view_box_height: 1
  color: #ff7019
  opacity: 1

# レイヤー移動
layer_element:
  element_id: <ID>
  position: back  # or front

# グループ解除
ungroup_elements:
  element_id: <GROUP_ID>

# テキスト移動
position_element:
  element_id: <ID>
  top: 1020    # Y位置（縦）
  left: 60     # X位置（横）

# テキスト色変更
format_text:
  element_id: <ID>
  formatting:
    color: "#ffffff"

# 不透明度変更（ロゴ等）
update_opacity:
  element_id: <ID>
  opacity: 0.75

# 要素削除
delete_element:
  element_id: <ID>
```
