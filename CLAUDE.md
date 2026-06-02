# CA・ST 広告運用ワークスペース

塾講師ステーションキャリア（CA）・塾講師ステーション（ST）の
Meta広告・Google広告運用メンバー向けClaude Codeワークスペース。

---

## 必ず最初に読むファイル

| ファイル | 内容 |
|---|---|
| `knowledge/business-overview.md` | CA・ST事業概要・KPI・タイムラグ・運用ルール |
| `knowledge/bigquery-schema.md` | BigQueryビュー名・カラム定義・クエリパターン |
| `knowledge/meta-ads-naming.md` | Meta広告命名規則マスタ（訴求軸・動画の型） |

---

## フォルダ構成

```
claude-code-template_af/
├── .claude/
│   ├── rules/        # Claudeの振る舞いルール（meta-ads-analysis.md含む）
│   ├── skills/       # スキル定義（setup, gdoc, gdrive, write-sheet等）
│   ├── agents/       # エージェント定義（ads-analyst, google-workspace）
│   └── hooks/        # 自動実行フック（シークレット検知・トークン更新等）
├── knowledge/        # 事前配布ナレッジ（セットアップ後すぐ使える）
├── secrets/          # 認証情報（.gitignore済・token.json配置先）
└── scripts/          # ユーティリティ（再認証・セキュリティアラート）
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

---

## BigQuery 接続情報

| 項目 | 値 |
|---|---|
| プロジェクトID | `bigquery-jukust` |
| リージョン | `asia-northeast1` |
| 認証 | `secrets/token.json`（OAuth・サービスアカウント禁止） |

詳細は `knowledge/bigquery-schema.md` を参照。

---

## Claudeへの指示

- コードを生成・修正する際は、トークンのハードコードが混入していないか厳重にセルフチェックすること
- 分析結果は必ず「結論 → 根拠データ → 推奨アクション」の順で出力すること
- KPI評価は**直近90日累計**ベース。週次数値は「参考のみ」として扱うこと
- Meta FV登録→面談申込は中央値40日のラグがある。直近40日以内のCV数は過小評価として扱うこと
- 月間広告費を10%以上超過させる変更の前に必ず確認を取ること
- 命名規則の解釈は `knowledge/meta-ads-naming.md` のマスタ準拠で行うこと（自己解釈禁止）
