## 開発・セキュリティ・運用ガイドライン

### 1. 認証とシークレット管理（最重要）
- **シークレットのハードコード禁止**: APIキー、パスワード、トークンの直書き（例: `api_key = 'sk...'`）を厳禁します。スレッドへの貼り付けも禁止です。
- **環境変数の利用**: 全ての機密情報は `.env` または `secrets/` フォルダ内の外部ファイル（`token.json`等）から動的に読み込んでください。
- **`.env` / 認証ファイルの標準パス（スキル・スクリプト作成時は必ずこのパスを使うこと）**:
  ```python
  ENV_FILE   = r"{{PROJECT_ROOT}}\.env"
  TOKEN_FILE = r"{{PROJECT_ROOT}}\secrets\token.json"
  CREDS_FILE = r"{{PROJECT_ROOT}}\secrets\credentials.json"
  ```
- **Google OAuth スコープ（統一指定）**: スキル・スクリプトでGoogle APIを使う場合、以下のスコープをそのまま使うこと。個別に絞らない（スコープ不足で再認証が発生するため）。
  ```python
  SCOPES = [
      'https://www.googleapis.com/auth/documents',
      'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets',
      'https://www.googleapis.com/auth/calendar',
      'https://www.googleapis.com/auth/calendar.events',
      'https://www.googleapis.com/auth/tasks',
      'https://www.googleapis.com/auth/bigquery',
  ]
  ```
- **BigQuery認証**: BigQueryはOAuthユーザー認証（token.json）を使うこと。サービスアカウント（gdrive-service-account.json等）はBigQuery権限がないため使用禁止。
  ```python
  PROJECT_ID = "bigquery-jukust"
  creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
  client = bigquery.Client(project=PROJECT_ID, credentials=creds)
  ```
- **GCPプロジェクト標準**: BigQueryプロジェクトは `bigquery-jukust`。
- **デプロイ時**: 本番へのデプロイ時は `.env` ではなく `Google Cloud Secret Manager` を使用してください。

### 2. データアクセスと個人情報保護
- **個人情報の非表示**: メーリスや電話番号などの個人情報をそのまま扱わず、マスキング済みViewを参照してください（例: `user_xxx@***.com` 形式）。
- **BigQuery利用**: 広告等の機密データは、直接APIを叩かずBigQueryに集約されたものを利用してください。
- **クエリの監視**: AIエージェントにクエリを実行させる場合は、事前に件数やスキャン量を確認し、無限ループや過剰スキャンを避けてください。

### 3. セキュリティインシデントへの対応
- **自動検知アラート**: 万が一、機密トークンの露出を検知した場合は、直ちに通知スクリプトを実行してください：
  `python scripts/security_alert.py "【重大】機密情報の露出を検知しました。至急修正が必要です。"`

### 4. ツール・環境
- **環境統一**: 基本的に `Claude Code` (VS Code拡張機能など) を通じて作業し、フォルダ全体を参照可能な状態で開発してください。
- **信頼性の確保**: 公式ドキュメントにない不明なパッケージのインストールや、GitHubの未確認スクリプトの実行は禁止です。
