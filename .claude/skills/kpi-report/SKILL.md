
---
name: kpi-report
description: 「KPI報告して」「週次報告」「月次レポート」「KPIまとめて」など、Meta広告のKPI報告・分析レポートを依頼されたときに発動。CA・ST両対応。ST：BigQueryで週次・CTA別・CR別データをすべて取得（集計さんシート不要）→ST_KPI報告の入力タブから予算補完→4セクション形式で出力。CA：BigQueryデータ取得→結論・根拠・アクションの順でレポートを出す。
---

## モード判別

依頼内容に応じて以下のモードを選択する:

| キーワード | モード |
|---|---|
| 「ST」「塾講師ステーション」「ST広告」「ST週次」 | **ST モード** |
| 「CA」「キャリア」またはキーワードなし | **CA モード** |

---

# ST モード

## このスキルの流れ（ST）

```
STEP 1: adset名一覧確認（初回のみ）
        python3 scripts/kpi/kpi_report_st.py --list-adsets

STEP 2: ADSET_GROUPS のキーワードを設定してからレポート実行
        python3 scripts/kpi/kpi_report_st.py 2026/05/01-2026/05/07

STEP 3: コンソール出力を確認後、スプシに書き込む
        python3 scripts/kpi/kpi_report_st.py 2026/05/01-2026/05/07 --write
```

**スクリプト仕様（v3）:**
- 期間は引数で必ず指定する（`YYYY/MM/DD-YYYY/MM/DD` 形式）
- adset_name キーワードで任意の分類（顕在/潜在など）に振り分け
- 応募CPA に対して OK / △ / NG 評価を付ける
- GEMINI_API_KEY（`.env`）が設定されていれば Gemini 2.5 Pro で4セクション自動生成
- `--write` で ST_KPI報告シートとテキストシートに書き込み

---

## STEP 1（ST）: 事前準備

### 初回のみ: adset名確認

```bash
python3 scripts/kpi/kpi_report_st.py --list-adsets
```

出力される adset_name 一覧を確認し、スクリプト冒頭の `ADSET_GROUPS` にキーワードを設定する:

```python
ADSET_GROUPS = {
    '顕在層': ['顕在'],
    '潜在層': ['潜在'],
    # 実際のadset_name に合わせて追記
}
```

### Gemini API 設定（初回のみ）

`.env` に以下を追記する（値はユーザーが記入）:

```
GEMINI_API_KEY=AIza...
```

### 必読ファイル（Gemini 未設定時にClaudeが分析する場合）

| ファイルパス | 読み取る情報 |
|---|---|
| `knowledge/business/business-overview.md` | 事業KPI・タイムラグ・評価サイクルの前提 |
| `knowledge/data/bigquery-schema.md` | BigQueryパターン |
| `knowledge/creative/meta-ads-naming.md` | 広告命名規則の読み方 |
| `.claude/rules/meta-ads-analysis.md` | 分析ルール・証拠強度・レポート形式 |
| `knowledge/business/fy26_meta_ads_overview.md` | 当期ST戦略・KPI・予算方針 |
| `knowledge/target/Prerequisites/ST_05_大学生カレンダー.md` | 心理フェーズ・需要スコア |
| `knowledge/target/Prerequisites/ST_07_KPI評価ルール.md` | 応募CPA判定基準 |
| `knowledge/creative/creative_trend_insights.md` | CTA・訴求軸の成果傾向 |
| `knowledge/target/customer_info_st.md` | STターゲット属性・時期別心理フェーズ |
| `knowledge/target/who_what_how.md` | WHO/WHAT/HOW構造定義 |
| `knowledge/data/ST_Meta広告集計さん_KPI報告.md` | 出力フォーマット見本 |
| `knowledge/business/ST_Meta_LINE_戦略.md` | **【2026-09-30追加・必読】BigQueryの`complete_registration`/`purchase`は実態と4倍以上乖離するため使用禁止と明記されている。極端な数値（CPA¥100,000超・CV0等）が出た場合は必ずこのファイルのアドエビス実測ファネル表と突き合わせること（9/23-28週のレポートで実際にこれが原因の誤判定が発生した）** |

---

## STEP 2（ST）: スクリプト実行

```bash
# レポート生成（コンソール出力）
python3 scripts/kpi/kpi_report_st.py 2026/05/01-2026/05/07

# スプシにも書き込む
python3 scripts/kpi/kpi_report_st.py 2026/05/01-2026/05/07 --write
```

### スクリプトの出力内容

1. **全体KPI**: 広告費・LINE_CV・応募CV・全体CPA・CTR・CVR・予算進捗
2. **adset分類別KPI**: ADSET_GROUPS の分類ごとに spend / LINE_CV / 応募CV / 応募CPA / OK△NG評価
3. **CTA別KPI**: ペルソナLP / 塾ブランド診断 / 気軽に診断 / 新1年生 / SNS ORG
4. **クリエイティブ上位15件**: LINE登録CPA順
5. **Gemini生成テキスト**: 事象 / 要因仮説 / 示唆（WHO/WHAT/HOW） / ネクスト

### スプシ書き込み先（--write フラグ時）

```
SPREADSHEET_ID: 1xXeCl4Xbkxz-w_jT49TmA3-voruL2cTbF1f308hZ5vQ
```

| シート名 | 書き込み内容 |
|---|---|
| `ST_KPI報告` | 当週列・累積列に LINE_CV / 応募CV / 応募CPA / COST / CTA別CV を書き込む |
| `KPI報告 のコピー` | Q30/U30/Y30/AC30 にGemini生成テキスト（事象・要因仮説・示唆・ネクスト）を書き込む |

### 注意事項

- `complete_registration` = LINE登録CV（メインKPI）
- `custom_cv_2` = 応募CV候補（LINE登録CVと同値なら BQ未分離 → N/A扱い）
- `target_date` を使うこと（`date` カラムは存在しない）
- spend < 1万円は統計的に不安定なため除外
- 直近40日以内の応募CVは過小評価の可能性あり（タイムラグ中央値40日）

---

## STEP 3（ST）: スプシ書き込み確認

`--write` 実行前にコンソール出力を確認し、数値に問題がなければ書き込みを実行する。

### 書き込み先セル詳細（ST_KPI報告シート）

| 行 | 内容 |
|---|---|
| 行10 | 月週ラベル（D〜R列）← 週列・累積列の特定に使う |
| 行15 | LINE_CV |
| 行26 | 応募CPA |
| 行27 | COST |
| 行35 | 応募CV実績 |
| 行45-49 | CTA別 LINE登録CV |
| 行54-58 | CTA別 応募CV |

### 書き込み先セル詳細（KPI報告 のコピーシート）

| セル | 内容 |
|---|---|
| Q30 | ★事象（Gemini生成） |
| U30 | ★要因仮説（Gemini生成） |
| Y30 | ★示唆（Gemini生成） |
| AC30 | ★ネクスト（Gemini生成） |
| AL2:AR10 | 月次KPIデータ（直近6ヶ月 / チャート自動更新用） |

> **月次チャートについて**: `create_monthly_charts.py` で作成した8本の折れ線グラフ（LINE登録CV / 応募CV / 応募CPA / COST / CPF / CTR / CVR / CPM）の元データが AL2:AR10 に書き込まれ、チャートが自動更新される。初回のみ `python3 scripts/kpi/create_monthly_charts.py` の実行が必要（作成済み）。

---

## STEP 3b（任意）: creative_trend_insights.md を更新する

**トリガー**: 「insights更新して」「シナリオ向けに傾向更新して」「クリエイティブ傾向まとめて」と言われたら実行。

### 実行手順

```bash
python3 scripts/analysis/analyze_recent_creatives.py
```

→ `scripts/data/recent_creative_analysis.json` に分析結果が出力される。

### 更新するセクション

JSONを読み込み、`knowledge/creative/creative_trend_insights.md` の以下セクションを上書きする:

| セクション | 更新内容 |
|---|---|
| `分析スコープ` | 期間・対象広告数・spend合計・CV合計 |
| `1. CTA別成果` | ペルソナLP / ブランド診断 / 気軽に診断 の CPA・CV・広告数・前回比 |
| `2. 訴求セグメント別成果` | タイパ / 単願 / 併願 の CPA・CV・spend |
| `3. 直近TOPクリエイティブ` | CPA昇順上位5件・勝ちパターンの共通要素 |
| `シナリオ設計ガイドライン` | 月・直近データを踏まえた推奨訴求・NG訴求 |
| `今月の季節変数` | 更新日・月の需要スコア・心理フェーズ・推奨CTA |

### 更新後の確認

- ファイル冒頭の更新日と末尾の `次回更新:` を今日の日付に変更する
- `create-scenario` スキル実行時に最新データが自動で反映される

---

# CA モード

## このスキルの流れ（CA）

1. **STEP 1**: 必読7ファイルをすべて読み込む
2. **STEP 2**: BigQuery から直近90日分のデータを取得する
3. **STEP 3**: KPI・クリエイティブ評価を実施する
4. **STEP 4**: 動画クリエイティブを6指標でチェックする
5. **STEP 5**: レポートを出力する（結論 → 根拠データ → 推奨アクション）
6. **STEP 6**: スプシ / Googleドキュメントへ書き込む（任意）

---

## STEP 1（CA）: 必読7ファイルの読み込み

以下を**すべて**読んでから分析を始める。1ファイルでも欠けたまま進まない。

| ファイルパス | 読み取る情報 |
|---|---|
| `knowledge/business/business-overview.md` | 事業KPI・タイムラグ・評価サイクルの前提 |
| `knowledge/data/bigquery-schema.md` | ビュー名・カラム定義・クエリパターン |
| `knowledge/creative/meta-ads-naming.md` | 命名規則の読み方（訴求軸・動画の型） |
| `.claude/rules/meta-ads-analysis.md` | 分析ルール・レポート形式 |
| `knowledge/business/fy26_meta_ads_overview.md` | 当期のKPI・予算・戦略方針 |
| `knowledge/business/fy25_meta_ads_strategy.md` | 過去の勝ちパターン・失敗パターン |
| `knowledge/creative/video_analysis_elements.md` | 動画クリエイティブ評価の6指標（フック・ベネフィット・テンポ・T&M・CTA・季節変数） |

---

## STEP 2（CA）: BigQuery からデータ取得

### 認証

```python
# スクリプトからの相対パス（ユーザー名に依存しない）
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "secrets", "token.json")
PROJECT_ID = "bigquery-jukust"
```

### 取得ルール

- 評価対象は **直近90日累計**（週次は参考のみ）
- クエリは必ず **CTEパターン**で書く（ビューに直接 GROUP BY+HAVING を書かない）
- `spend < 1万円` の広告は統計的に不安定なため除外

### 基本クエリ（広告別90日集計）

```sql
WITH agg AS (
  SELECT
    ad_name,
    SUM(spend)       AS spend,
    SUM(purchase)    AS purchase,
    SUM(link_clicks) AS link_clicks
  FROM `bigquery-jukust.dataset.v_CA_meta_ads_daily_report_with_scenario`
  WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
  GROUP BY ad_name
)
SELECT
  ad_name,
  spend,
  purchase,
  SAFE_DIVIDE(spend, purchase)       AS cpa,
  SAFE_DIVIDE(purchase, link_clicks) AS cvr
FROM agg
WHERE spend >= 10000
ORDER BY cpa ASC
```

---

## STEP 3（CA）: KPI・クリエイティブ評価

1. **CPA ランク付け**: spend ≥ 1万円の広告を CPA 昇順でランク付け
2. **命名規則解析**: `ad_name` を `knowledge/creative/meta-ads-naming.md` に照らし、訴求軸・動画の型を分類（自己解釈禁止）
3. **デモグラ確認**: デモグラビューで 25-34歳 の CVR をベースラインと比較
4. **タイムラグ考慮**: 直近40日以内の CV 数は過小評価として扱う

---

## STEP 4（CA）: 動画クリエイティブ評価（6指標チェック）

`knowledge/creative/video_analysis_elements.md` の6指標に沿って上位・下位クリエイティブを評価する。

| 指標 | 確認ポイント |
|---|---|
| **① 冒頭のフック** | ターゲットが「自分に関係ある」と0.5秒以内に認識できるか |
| **② メッセージ・ベネフィット** | ペインポイントへの解決策がユーザー視点で語られているか |
| **③ テンポ・情報量** | カット割りが間延びせず、テキスト視認性が確保されているか |
| **④ トーン&マナー** | BGM・色調・登場人物がターゲットに適しているか |
| **⑤ CTA** | 「次に何をすればいいか」が迷いなく提示されているか |
| **⑥ 季節変数** | 配信時期のインサイト（行事・心理）と動画メッセージが連動しているか |

---

## STEP 5（CA）: レポート出力

以下の順序で必ず出力する。

### 1. 結論（1〜2行で即答）

最良クリエイティブ / 主要課題を端的に。

### 2. 根拠データ（表）

```
| ad_name | spend | purchase | CPA | CVR |
|---|---|---|---|---|
```

### 3. 推奨アクション（優先度付き・3件以内）

- 優先度が高い順に列挙
- 各アクションに証拠強度を付ける

| 強度 | 基準 | 表記 |
|---|---|---|
| ★★★ | BigQueryデータで直接示せる事実 | そのまま断言 |
| ★★ | 間接的・複数データが一致 | 「〜と推測される」 |
| ★ | 論理的推測 | 「推定:〜」と明記 |

---

## STEP 6（CA）: 出力先への書き込み（任意）

| 出力先 | スキル | 用途 |
|---|---|---|
| スプレッドシート | `write-sheet` | 集計数値テーブル |
| Googleドキュメント | `gdoc` | 分析レポート・インサイト整形 |

**書き込み前は必ず1行確認を取る。**
