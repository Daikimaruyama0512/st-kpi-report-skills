# CA・ST 広告運用 Claude Code テンプレート

塾講師ステーションキャリア（CA）・塾講師ステーション（ST）の
Meta広告・Google広告運用メンバー向けClaude Codeテンプレート。

事業知識・BigQueryスキーマ・Meta広告命名規則がセットアップ時点から `knowledge/` に同梱されている。

---

## クイックスタート

### 事前準備（手動）

1. **Claude Code をインストール**: `npm install -g @anthropic-ai/claude-code`
2. **[Google Drive](https://drive.google.com/drive/folders/1GWBBjn3SrROpWYfI83RmJCqWrR8Wt_38) から `credentials.json` をDL**
3. **credentials.json を `secrets/` に配置**

### セットアップ（自動）

```
1. このフォルダを自分の作業ディレクトリにコピー
2. Claude Code を起動
3. 「セットアップして」と入力
4. 対話に答えるだけで完了（約5分）
```

自動実行される処理:
- プレースホルダー一括置換（`.claude/`・`CLAUDE.md`・`knowledge/` 全ファイル）
- `.env` の作成
- npm グローバルパッケージのインストール（MCP サーバー群）
- Google OAuth認証の実行（token.json生成）
- ホームディレクトリ設定（`~/.claude/`）

---

## 含まれるもの

### Knowledge（事前配布ナレッジ）— セットアップ後すぐ使える

| ファイル | 内容 |
|---------|------|
| `business-overview.md` | CA・ST事業概要・KPI・タイムラグ・運用ルール |
| `bigquery-schema.md` | BigQueryビュー名・カラム定義・クエリパターン |
| `meta-ads-naming.md` | Meta広告命名規則マスタ（訴求軸・動画の型） |

### Rules（ルール）— Claudeの振る舞いを制御

| ファイル | 内容 |
|---------|------|
| `meta-ads-analysis.md` | Meta広告分析ルール・評価基準・予算管理ルール |
| `output-style.md` | 日本語出力・結論→根拠→アクション |
| `python-coding.md` | UTF-8・BigQuery CTE・pandas |
| `security.md` | シークレット管理・OAuth認証パス |
| `context-management.md` | /compact・plan mode活用 |

### Skills（スキル）— Claudeに「できること」を教える

| スキル | 発動ワード | 内容 |
|--------|-----------|------|
| `setup` | 「セットアップして」 | 初期セットアップ自動実行 |
| `audio-transcriber` | 「文字起こしして」 | 音声→議事録 |
| `gdoc` | 「ドキュメントにして」 | Googleドキュメント作成 |
| `gdrive` | 「ドライブ検索して」 | Googleドライブ検索 |
| `google-calendar` | 「カレンダーに登録して」 | タスク登録 |
| `write-sheet` | 「スプシに書いて」 | スプレッドシート書き込み |

### Agents（エージェント）— スキルをまとめた専門家

| エージェント | 担当スキル | 用途 |
|------------|-----------|------|
| `ads-analyst` | gdoc, write-sheet | Meta/Google広告データ分析 |
| `google-workspace` | gdoc, gdrive, write-sheet | GWS操作全般 |

### Hooks（フック）— 自動で動くバックグラウンド処理

| フック | タイミング | 内容 |
|-------|-----------|------|
| `pre-write-secrets-scan.py` | ファイル書き込み前 | シークレット検知→ブロック |
| `post-compact-inject.py` | /compact後 | 重要ルール再注入 |
| `refresh-google-tokens.js` | 毎メッセージ送信時 | Googleトークン自動更新 |

---

## BigQuery 接続情報

- **プロジェクトID**: `bigquery-jukust`（セットアップ時に自動設定済み）
- **リージョン**: `asia-northeast1`（東京）
- **主要ビュー**: `knowledge/bigquery-schema.md` 参照

---

## カスタマイズガイド

### 自分のスキルを追加する

1. `.claude/skills/スキル名/SKILL.md` を作成
2. フロントマターで `name` / `description` を定義
3. 手順をMarkdownで記述

### Slack通知を追加する

`samples/hooks/` の `slack-notify.py` を参考に `.claude/hooks/` に配置し、
`settings.local.json` の hooks セクションに登録する。

---

## サンプル集（samples/）

そのままでは動かないが、設計パターンの参考として活用してください。
→ 詳細は `samples/README.md` を参照

---

## Google OAuth の準備

セットアップの前に以下の手動作業が必要:

1. [Google Driveフォルダ](https://drive.google.com/drive/folders/1GWBBjn3SrROpWYfI83RmJCqWrR8Wt_38) から `credentials.json` をダウンロード
2. ダウンロードしたファイルを `secrets/credentials.json` として配置
3. Claude Code を起動して「セットアップして」→ 自動で `token.json` が生成される

---

## トラブルシューティング

### Google認証エラー
- `token.json` を削除して再認証: `rm secrets/token.json` → 「セットアップして」
- スコープ不足: `credentials.json` を再作成してやり直す

### BigQueryに接続できない
- `token.json` が `bigquery` スコープを含んでいるか確認
- `python scripts/reauth_google.py` で再認証する

### Hookが動かない
- `settings.local.json` のパスが正しいか確認
- Python/Node.js がPATHに通っているか確認

### スキルが発動しない
- `.claude/skills/スキル名/SKILL.md` が正しい場所にあるか確認
- `description` にトリガーワードが含まれているか確認
