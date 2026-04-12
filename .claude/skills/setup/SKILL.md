---
name: setup
description: "「セットアップして」「初期設定して」「setup」と言ったときに発動。プロジェクトのプレースホルダーを自動置換し、npm パッケージのインストール、Google OAuth認証、ホームディレクトリ設定までを一気通貫で実行する。"
allowed-tools: "Bash,Read,Write,Edit,Glob,Grep"
---

## 概要

このスキルはClaude Code テンプレートの初期セットアップを自動実行する。
ユーザーに対話で質問しながら、Phase 1〜8 を順に処理する。

**重要**: 各Phaseの完了後に結果を表示し、次のPhaseに進む前に問題がないか確認する。

---

## Phase 1: 環境情報の自動取得

以下をBashで自動取得する（ユーザーに聞かない）:

```bash
# プロジェクトルートを取得
pwd

# Windowsユーザー名を取得
whoami
```

取得した値を変数として保持:
- `PROJECT_ROOT` ← `pwd` の結果（Windowsパス形式に変換: `/c/Users/...` → `C:\Users\...`）
- `USERNAME` ← `whoami` の結果からユーザー名部分を抽出

**BigQueryプロジェクトIDは `bigquery-jukust` で固定**（ユーザーに聞かない）。

---

## Phase 2: プレースホルダー一括置換

`.claude/` 配下の全ファイル、`CLAUDE.md`、`knowledge/` 配下の全ファイルで以下を置換する。
`knowledge/` フォルダ内のプレースホルダーも置換対象に含まれる。

```bash
# 対象ファイルを列挙
find . -path ./samples -prune -o -path ./secrets -prune -o \( -name "*.md" -o -name "*.json" -o -name "*.json.example" -o -name "*.py" -o -name "*.js" \) -print
```

置換ルール:
| プレースホルダー | 置換値 |
|---|---|
| `{{PROJECT_ROOT}}` | Phase 1で取得したプロジェクトルート |
| `{{USERNAME}}` | Phase 1で取得したユーザー名 |

置換には `python -c` ワンライナーまたは `sed` を使う。

**置換完了後**: 置換されたファイル数と残留プレースホルダー数を表示する。

---

## Phase 3: 設定ファイルのコピー

```bash
# settings.local.json.example → settings.local.json にコピー（既に置換済み）
cp .claude/settings.local.json.example .claude/settings.local.json
```

---

## Phase 4: .env セットアップ

**セキュリティ上、APIキーやWebhook URLをチャットで聞いてはいけない。**

`.env.example` を `.env` にコピーし、ユーザーにファイルを直接編集してもらう:

```bash
cp .env.example .env
```

コピー後、以下のメッセージを表示:

```
.env ファイルを作成しました。
Slack通知を使う場合は、.env をエディタで開いて以下の値を入力してください:

  SLACK_WEBHOOK_URL=（Slack Incoming WebhookのURL）
  SLACK_CHANNEL=（通知先チャンネルID or 名前）

不要な場合はそのままで問題ありません。準備できたら「続けて」と言ってください。
```

---

## Phase 5: npm グローバルパッケージ

まず既存のインストール状況を確認:

```bash
npm list -g --depth=0 2>/dev/null
```

以下の必須パッケージが未インストールなら `npm install -g` を実行:

| パッケージ | 用途 | 条件 |
|-----------|------|------|
| `mcp-google-sheets` | Google Sheets MCP | 常にインストール |
| `google-calendar-mcp` | Google Calendar MCP | 常にインストール |
| `@modelcontextprotocol/server-gdrive` | Google Drive MCP | 常にインストール |
| `@ergut/mcp-bigquery-server` | BigQuery MCP | 常にインストール |

インストール前にユーザーに確認: 「以下のパッケージをグローバルインストールします。よいですか？」

---

## Phase 5.5: BigQuery認証（gcloud CLI ADC設定）

### 5.5.1 gcloud CLI存在確認

```bash
gcloud --version 2>/dev/null
```

### 5.5.2-A インストール済みの場合

ADC（Application Default Credentials）を設定する:
```bash
gcloud auth application-default login
```
ブラウザが開くので、ユーザーにGoogleアカウントで承認してもらう。承認完了後、Phase 5.6 に進む。

### 5.5.2-B 未インストールの場合（winget自動インストール）

ユーザーに確認: 「gcloud CLIが未インストールです。winget経由で自動インストールしますか？（y/n）」

y の場合:

```bash
winget install --id Google.CloudSDK -e --silent --accept-source-agreements --accept-package-agreements
```

**winget自体が無い場合**のフォールバック案内:
```
winget が利用できません。以下から手動でインストーラーをダウンロードしてください:
  https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe

インストール後、Claude Codeを再起動して「セットアップして」をもう一度実行してください。
```

**wingetインストール成功時**: 以下のメッセージを表示してsetup処理を**中断**する。

```
gcloud CLIをインストールしました。
PATHを反映させるため、Claude Codeを一度終了して再起動してください。
再起動後にもう一度「セットアップして」と入力すれば、
ADC設定から続きを実行します。
```

**重要**: インストール直後は同一シェルでは `gcloud` が見つからない可能性が高い。
再起動後の2回目の実行では `gcloud --version` が通るので、そのまま 5.5.2-A のフローに進める。

---

## Phase 5.6: Python BQパッケージのインストール

```bash
pip install google-cloud-bigquery db-dtypes pyarrow google-auth-oauthlib google-auth-httplib2 google-api-python-client 2>/dev/null
```

インストール前にユーザーに確認: 「BigQuery用のPythonパッケージをインストールします。よいですか？」

---

## Phase 6: Google OAuth認証

### 6-1. secrets/ フォルダの確認

```bash
# secrets/ フォルダがなければ作成
mkdir -p secrets
```

### 6-2. credentials.json の確認

```bash
ls secrets/credentials.json 2>/dev/null
```

- **存在する場合**: 「credentials.json を検出しました。Google認証を実行します。」
  → `python scripts/reauth_google.py` を実行（スクリプトが存在する場合）
  → スクリプトが存在しない場合は Phase 6-3 のインライン認証を実行

- **存在しない場合**: 以下の手順を表示して待機:
  ```
  credentials.json が見つかりません。以下の手順で準備してください:

  1. 以下のGoogle Driveフォルダから credentials.json をダウンロード
     https://drive.google.com/drive/folders/1GWBBjn3SrROpWYfI83RmJCqWrR8Wt_38
  2. ダウンロードしたファイルを secrets/credentials.json として配置
  3. 配置したら「続けて」と言ってください
  ```

### 6-3. token.json の生成

credentials.json が配置されたら:
```python
# reauth_google.py と同等の処理
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/bigquery',
]
flow = InstalledAppFlow.from_client_secrets_file('secrets/credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
with open('secrets/token.json', 'w') as f:
    f.write(creds.to_json())
```

ブラウザが開くので、ユーザーにGoogleアカウントで承認してもらう。

---

## Phase 7: ホームディレクトリ設定

### 7-1. ~/.claude/settings.json

```bash
cat ~/.claude/settings.json 2>/dev/null
```

- **存在しない場合**: 推奨設定を書き込む:
  ```json
  {
    "permissions": { "defaultMode": "allowEdits" },
    "model": "sonnet"
  }
  ```

- **既に存在する場合**: 「~/.claude/settings.json が既にあります。上書きしますか？（y/n）」と確認

### 7-2. ~/.claude/CLAUDE.md

- **存在しない場合**: テンプレートを書き込む:
  ```markdown
  # グローバル設定

  ## Google認証
  どの作業フォルダから起動していても、以下のパスを使うこと:
  TOKEN_FILE = r"{PROJECT_ROOT}\secrets\token.json"
  CREDS_FILE = r"{PROJECT_ROOT}\secrets\credentials.json"

  ## 言語
  出力は常に日本語。
  ```
  ※ `{PROJECT_ROOT}` は Phase 1 で取得した実際の値に置換する

- **既に存在する場合**: 「~/.claude/CLAUDE.md が既にあります。スキップします。」

### 7-3. .gitconfig 確認

```bash
git config --global user.name
git config --global user.email
```

未設定の場合は案内:
```
git の名前・メールが未設定です。以下を実行してください:
  git config --global user.name "あなたの名前"
  git config --global user.email "your-email@tomonokai-corp.com"
```

---

## Phase 8: 最終検証

### 残留プレースホルダーチェック

```bash
grep -r "{{PROJECT_ROOT}}\|{{USERNAME}}\|N0079" --include="*.md" --include="*.json" --include="*.py" --include="*.js" . 2>/dev/null | grep -v samples/ | grep -v node_modules/
```

### 結果サマリーを表示

```
===== セットアップ完了 =====

[環境情報]
- プロジェクトルート: {PROJECT_ROOT}
- ユーザー名: {USERNAME}
- BigQuery: bigquery-jukust（固定）

[ファイル]
- プレースホルダー置換: N 件完了
- settings.local.json: 作成済み
- .env: 作成済み

[npm パッケージ]
- mcp-google-sheets: OK
- google-calendar-mcp: OK
- @modelcontextprotocol/server-gdrive: OK
- @ergut/mcp-bigquery-server: OK

[BigQuery]
- gcloud CLI: あり/なし
- ADC (application-default): 設定済み/未設定
- Pythonパッケージ (google-cloud-bigquery等): インストール済み

[Google認証]
- credentials.json: あり/なし
- token.json: あり/なし

[ホーム設定]
- ~/.claude/settings.json: あり
- ~/.claude/CLAUDE.md: あり

[残留チェック]
- 未置換プレースホルダー: 0 件（問題なし）
```

問題がある場合は警告を表示し、対処方法を案内する。
