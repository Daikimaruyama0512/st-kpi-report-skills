# CA・ST 広告運用ワークスペース

塾講師ステーションキャリア（CA）・塾講師ステーション（ST）の
Meta広告・Google広告運用メンバー向けClaude Codeワークスペース。

---

## 必ず最初に読むファイル

| ファイル | 内容 |
|---|---|
| `knowledge/business/business-overview.md` | CA・ST事業概要・KPI・タイムラグ・運用ルール |
| `knowledge/data/bigquery-schema.md` | BigQueryビュー名・カラム定義・クエリパターン |
| `knowledge/creative/meta-ads-naming.md` | Meta広告命名規則マスタ（訴求軸・動画の型） |

---

## フォルダ構成

```
claude-code-template_af/
├── .claude/
│   ├── rules/        # Claudeの振る舞いルール（meta-ads-analysis.md含む）
│   ├── skills/       # スキル定義（setup, gdoc, gdrive, write-sheet等）
│   ├── agents/       # エージェント定義（ads-analyst, google-workspace）
│   └── hooks/        # 自動実行フック（シークレット検知・トークン更新等）
├── knowledge/
│   ├── business/     # 事業・戦略ドキュメント（business-overview, fy26/fy25 overview）
│   ├── target/       # ターゲット・インサイト（customer_info, who_what_how, Prerequisites/）
│   ├── creative/     # クリエイティブ・シナリオ（meta-ads-naming, sns_ads_scenario_master等）
│   └── data/         # データ・KPI参照（bigquery-schema, ST_Meta集計さん等）
├── scripts/
│   ├── kpi/          # KPI報告・グラフ生成（kpi_report_st/ca, create_monthly_charts）
│   ├── sheets/       # スプレッドシート操作・タブ作成
│   ├── analysis/     # クリエイティブ・シナリオ分析
│   ├── read/         # シート・ドキュメント読み取り
│   ├── utils/        # ユーティリティ（reauth_google, security_alert, update_seasonal_insights）
│   └── data/         # 出力データ（JSON/CSV）
├── secrets/          # 認証情報（.gitignore済・token.json配置先）
```

---

## キーワード → スキル・エージェント対応

| キーワード | 発動するもの |
|---|---|
| 「シナリオ作って」「〇月用のシナリオ」「シナリオ修正して」 | create-scenario スキル |
| 「KPI報告して」「週次報告」「月次レポート」「KPIまとめて」 | kpi-report スキル |
| 「広告分析して」「CPAが知りたい」「クリエイティブ評価して」 | ads-analyst エージェント |
| 「シナリオ分析して」「訴求軸を評価して」「YoY比較して」 | ads-analyst エージェント |
| 「スプシに書いて」「スプレッドシートに記入して」 | write-sheet スキル |
| 「ドキュメントにして」「整形して」 | gdoc スキル |
| 「ドライブ検索して」 | gdrive スキル |
| 「カレンダーに登録して」「タスク追加して」 | google-calendar スキル |
| 「文字起こしして」「議事録作って」 | audio-transcriber スキル |
| 「セットアップして」 | setup スキル |
| 「CanvaのStoriesを改善して」「LPに合わせてデザインを直して」「背景を差し替えて」「テキストレイアウトを整えて」「Canvaのデザインを編集して」 | canva-story-design スキル |
| 「黄金比に近づけて」「配置の比率を最適化して」「余白を整えて」「LPのレイアウトを改善して」 | lp-layout スキル |
| 「コピーのバリエーションを出して」「キャッチコピーを複数案作って」「A/Bテスト用のコピーがほしい」「FVのコピーを考えて」 | lp-copy-variants スキル |
| 「LPを作って」「ランディングページを作って」「競合を参考にLPを作りたい」「新しいLPを作って」 | lp-create スキル |

---

## BigQuery 接続情報

| 項目 | 値 |
|---|---|
| プロジェクトID | `bigquery-jukust` |
| リージョン | `asia-northeast1` |
| 認証 | `secrets/token.json`（OAuth・サービスアカウント禁止） |

詳細は `knowledge/data/bigquery-schema.md` を参照。

---

## セッション引き継ぎ（コンテキスト管理）

フックが自動で監視する。警告が出たらメモを作成してセッションを区切ること。

| 通知 | 意味 | 対応 |
|---|---|---|
| ⚠️ ソフト警告 | 会話量がソフト閾値超 | キリよければ区切る。佳境なら続行可 |
| ⛔ ハード警告 | ハード閾値超 | いまの作業単位だけ終わらせ、即座に引き継ぎメモを作成して終了 |

### 引き継ぎメモの作成
`.claude/handoffs/YYYY-MM-DD_HH-MM-SS.md` にテンプレート（`TEMPLATE.md`）に従って書く。
**必須項目**: ゴール／いまの状態／編集途中のファイル／失敗した試みと理由（次セッションで同じ失敗を繰り返さないために必須）／次にやること
**ヘッダー**: `status: 引き継ぎ中` を必ず記載する。

次回セッション開始時に自動読み込みされ、「続き」の一言で再開できる。

---

## Claudeへの指示

- コードを生成・修正する際は、トークンのハードコードが混入していないか厳重にセルフチェックすること
- 分析結果は必ず「結論 → 根拠データ → 推奨アクション」の順で出力すること
- KPI評価は**直近90日累計**ベース。週次数値は「参考のみ」として扱うこと
- Meta FV登録→面談申込は中央値40日のラグがある。直近40日以内のCV数は過小評価として扱うこと
- 月間広告費を10%以上超過させる変更の前に必ず確認を取ること
- 命名規則の解釈は `knowledge/creative/meta-ads-naming.md` のマスタ準拠で行うこと（自己解釈禁止）
