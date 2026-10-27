"""
オンボーディングガイド 台本 自動生成スクリプト

Google Slides API で実際のスライド内容を読み込み、
各スライドに対応した口頭説明・補足知識・ハンズオン手順を
Google Doc（台本）として出力する。

スライドが更新されてもこのスクリプトを再実行すれば台本が再生成される。

使い方:
  python3 create_onboarding_narration.py                # 岩崎さん向け（バランス型）
  python3 create_onboarding_narration.py --target 新井  # 新井さん向け（運用・クリエイティブ重視）

必要: pip install google-api-python-client google-auth
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ターゲット判別
TARGET = "新井" if "--target" in sys.argv and "新井" in sys.argv else "岩崎"

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = "/Users/119322/Desktop/claude-code-template_af/secrets/token.json"
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
]

PRES_ID = "1G8dvo5k9m-XsxDL0r4NolNrvY7S8EKuMU2JWWSQSF_0"

# ─────────────────────────────────────────────────────────────────────
# スライドIDごとの台本データ
# スライドが更新されても slide_id キーで対応するため陳腐化しにくい
# ─────────────────────────────────────────────────────────────────────
NARRATION = {
    "slide01": {
        "section": "オープニング",
        "speech": """\
「今日は10月以降のメタ広告運用の引き継ぎをします。
スライドに沿って話しますが、わからないことはその都度聞いてください。
この仕事はClaude Codeというツールが大部分をサポートしてくれます。
最後にチェックリストで理解度を確認します。」""",
        "notes": [
            "レクチャー前の確認: Claude Code / secrets/token.json / BigQueryアクセス / Meta管理画面権限",
            "台本はそのまま読み上げてOK。補足知識は質問が来た時に使う",
        ],
        "handson": [],
    },

    "slide02": {
        "section": "AGENDA",
        "speech": """\
「今日話す内容は6つです。
① ST事業の概要、② KPIの仕組み、③ 業務フロー、
④ 使用ツール、⑤ LPとクリエイティブ、⑥ 分析とKPI報告の型。
最後にチェックリストで理解度を確認します。
だいたい1〜1.5時間で終わる想定です。」""",
        "notes": [
            "全体像を最初に見せることで、今どこにいるかがわかる",
            "6セクション全体の流れを口頭でも追って伝える",
        ],
        "handson": [],
    },

    "slide03": {
        "section": "① ST概要 ─ 事業概要",
        "speech": """\
「塾講師ステーション（ST）は、大学生向けの塾・家庭教師バイト専門求人サイトです。
ビジネスモデルは掲載課金——塾側が掲載費を払い、ユーザー（大学生）は無料で使えます。
私たちアフェニティチームの役割は、Meta広告でユーザーをLPに誘導し、LINE登録してもらうことです。
LINE登録した人が応募・採用されるほど塾の満足度が上がり、継続掲載につながります。
つまり私たちの成果がSTの収益に直結しています。」""",
        "notes": [
            "年間登録者約2.7万人、累計76万人の実績がある大手サービス",
            "競合: じゅくWork・ジュクコーシ・塾ナビ等",
            "私たちの仕事: 広告→LP→LINE登録→応募 の流れを最適化すること",
            "掲載課金モデル = 採用数が上がるほど塾が継続する → 応募数の改善が事業価値に直結",
        ],
        "handson": [],
    },

    "slide04": {
        "section": "① ST概要 ─ ターゲット3ペルソナ",
        "speech": """\
「広告で狙うターゲットは大学生（18〜22歳）で、3種類のペルソナがいます。
① タイパ重視（積極探し）: 効率よくバイトを見つけたい層。30秒で診断・すぐ応募 が刺さる。
② 単願（ミスマッチ回避・慎重型）: 1つの塾に集中したい。合う塾かどうかが不安な層。
③ 併願（比較型）: 複数を比較検討中。競合とも見比べている層。
クリエイティブを作るときは、このどのペルソナに向けて話すかを先に決めます。
1つのクリエイティブに複数のペルソナを詰め込むと、メッセージが散漫になりCV 0になりやすいです。」""",
        "notes": [
            "季節によってどのペルソナが強いかが変わる（大学生カレンダーを参照）",
            "9〜10月は就活・新学期モード → 単願・タイパが増える傾向",
            "知識ファイル: knowledge/target/Prerequisites/ 配下を参照",
        ],
        "handson": [],
    },

    "slide05": {
        "section": "② KPI体系 ─ KPIツリー",
        "speech": """\
「KPIのツリーはこうなっています。
IMP（表示）→ CTR → LP流入 → LINE登録（CV）→ 応募 → 採用 という流れです。
私たちが直接管理できるのは IMP・CTR・LP→LINE CVR の3つです。
LINE登録数がメインKPIで、ここを増やすことが最優先の仕事です。

主要な評価指標は2つ:
・LINE登録CPA（広告費 ÷ LINE登録数）: 顕在層 ¥1,500〜3,000 / 潜在層 ¥700〜1,500 が目安
・応募CPA（広告費 ÷ 応募数）: ¥20,000以下が良好」""",
        "notes": [
            "CPAの計算式: SAFE_DIVIDE(spend, complete_registration) — ゼロ除算を防ぐ",
            "CTR（クリック率）とCVR（LINE登録率）も週次でモニタリングする",
            "KPI評価の基準: spend ≥ ¥10,000 の広告のみを評価対象にする",
        ],
        "handson": [],
    },

    "slide06": {
        "section": "② KPI体系 ─ タイムラグの理解（重要）",
        "speech": """\
「ここは非常に重要です。LINE登録から応募まで、中央値で40日のタイムラグがあります。
LINE登録してすぐに応募する人は少なく、LINE内で情報収集してから1〜2ヶ月後に応募するパターンが多いためです。

これを理解していないと「先週CVゼロ」に焦って間違った判断をしてしまいます。

実務ルール（必ず守る）:
1. 直近40日以内のCV数は『過小評価』として扱う。少なくても焦らない。
2. KPI評価は直近90日累計ベース。タイムラグを吸収できる十分な期間。
3. 週次の数値変動には一喜一憂しない。あくまで速度感のチェックのみ。」""",
        "notes": [
            "タイムラグ中央値40日: knowledge/business/business-overview.md に記載",
            "90日未満のCPAは「参考値」として★★（推測）レベルで扱うこと",
            "週次のCPA急変は『異常値の検知』に使う（評価には使わない）",
        ],
        "handson": [],
    },

    "slide07": {
        "section": "③ 業務フロー ─ 週次・月次ルーティン",
        "speech": """\
「毎週の業務フローを説明します。
月曜: 先週のKPI集計。Claude Codeでkpi-reportスキルを実行して週次報告を作成。
火〜木: クリエイティブ評価（停止・継続・新規作成の判断）・BigQuery分析・LP改善。
金曜: 翌週クリエイティブの準備。Canvaで制作して命名規則チェック。
月末: 月次レポート作成と翌月のクリエイティブ計画を立てる。

実際にkpi-reportスキルを動かしてみましょう。」""",
        "notes": [
            "月次: 月初に先月KPI報告 → 中旬にA/Bテスト判定 → 月末に翌月シナリオ設計",
            "承認フロー: 予算10%超過変更は上長確認必須 / LP変更はペライチ担当に事前連絡",
        ],
        "handson": [
            "1. ターミナルでプロジェクトフォルダに移動: cd /Users/119322/Desktop/claude-code-template_af",
            "2. Claude Codeを起動",
            "3. 「STのKPI報告して 2026/09/01-2026/09/07」と入力",
            "4. 出力を確認: 全体KPI・adset分類別・クリエイティブ別が自動生成される",
            "5. スプシへの書き込みは --write フラグで実行（本番では確認してから）",
        ],
    },

    "slide08": {
        "section": "④ 使用ツール ─ ツール一覧",
        "speech": """\
「日常業務で使うツールです。
・Meta広告管理画面: 広告の入稿・予算設定・実績確認。ここのCV数値が正確。
・Canva: クリエイティブの動画・静止画制作。チームフォルダにテンプレートあり。
・ペライチ: LP公開・管理。変更前に担当者に事前連絡が必須。
・Claude Code: kpi-report・create-scenario・ads-analystなど業務スキルが入ってる。
・BigQuery: 広告データのデータベース。プロジェクト: bigquery-jukust。
・スプレッドシート（集計さん）: KPI記録・チャート。Claude Codeが自動書き込みする。

重要注意: BigQueryのCV（complete_registration）はビュースルーCVが含まれる可能性があります。
管理画面で28日クリック後 + 1日視聴後の設定で実数を確認することが必要です。
BQ値は参考値。最終判断は管理画面の数値で行ってください。」""",
        "notes": [
            "ビュースルーCV: 広告を見た（タップしていない）後に別経路でLINE登録した場合のCV",
            "BQとの乖離: 定期的に管理画面の実数と照合すること",
            "Claude Codeのスキル一覧: .claude/skills/ フォルダにマークダウンで定義されている",
        ],
        "handson": [
            "Claude Codeで使えるスキルを確認: 「kpi-report」「create-scenario」「ads-analyst」",
            "「広告分析して」「CPAが知りたい」と入力 → ads-analystエージェントが起動する",
        ],
    },

    "slide09": {
        "section": "⑤ LPガイド ─ LP構成",
        "speech": """\
「LPは広告がユーザーをどこに連れていくかを決める着地点です。
構成は上から: ① FV（最重要・ここで離脱率が決まる）→ ② 実績STATS → ③ 3ステップ → ④ 口コミ → ⑤ 差別化 → ⑥ ラストCTA。

現在のLPは3種類: ペルソナLP・塾ブランド診断LP・気軽に診断LP。
CVポイントは1つ: LINE友だち追加のみです。

FVで最も重要なのは『広告の訴求とFVのコピーが一致しているか』です。
ズレがあると、広告でクリックが取れてもLPで離脱します。
B2キャンペーン分析でも確認済みで、広告の訴求（夏・働きやすさ）がLPにない場合、CVゼロになっています。」""",
        "notes": [
            "LP評価基準: 応募CPA ¥30,000超かつ転換率10%未満でLPが原因の可能性",
            "LP改善の優先タスク: FVバリアント（シフト週1〜OK）の作成が残課題",
            "「稼いで」という表現は規約違反の可能性あり → 要確認",
            "lp/line_meta_IG.html がメインLPファイル（Gitで管理）",
        ],
        "handson": [],
    },

    "slide10": {
        "section": "⑤ クリエイティブガイド ─ 訴求軸・シナリオ設計",
        "speech": """\
「クリエイティブには5つの訴求軸があります。
・課題解決型: ペインを言語化（ミスマッチ回避層向け）
・ベネフィット型: 得られる未来を提示（タイパ重視層向け）
・数字型: 実績で信頼（慎重派向け）
・共感型: 感情に寄り添う（単願層向け）
・差別化型: 競合との違いを明示（比較型向け）

動画シナリオの型: フック（0〜3秒で止める）→ ボディ（問題提起→解決→実績）→ CTA（明確な行動促進）。
シナリオを作るときはClaude Codeの create-scenario スキルで自動生成できます。
1シーズン、各キャンペーンに5本が目安です。」""",
        "notes": [
            "勝ちパターン（2026年8月実績）: 単願訴求 × ブランド診断CTA が最良CPA（¥12,310）",
            "静止画でもCVが出る。フック文言が重要",
            "訴求は1本に絞る。複数詰め込みはCV 0になりやすい",
            "命名規則マスタ: knowledge/creative/meta-ads-naming.md を必ず確認",
        ],
        "handson": [
            "1. Claude Codeに「シナリオを作って」と入力",
            "2. ターゲットペルソナ・訴求軸・動画の型を対話的に選ぶ",
            "3. 生成されたシナリオをCanvaに貼り付けて制作",
        ],
    },

    "slide11": {
        "section": "⑥ 分析・KPI報告 ─ 分析の型",
        "speech": """\
「分析結果を報告するときは必ずこの順番で話します。
1. 結論（1〜2行で即答）: 例『○○クリエイティブのCPAが最良（¥18,920）』
2. 根拠データ（表形式で: ad_name / spend / purchase / CPA）
3. 推奨アクション（優先度付きで3件以内）

この型を守ると上長や関係者に伝わりやすくなります。

クリエイティブ評価の手順:
1. 評価期間は直近90日累計（週次は速度感チェックのみ）
2. spend ≥ ¥10,000 のみ評価対象（小額は統計的に不安定）
3. 命名規則で訴求軸・動画の型を分類してパターン分析する」""",
        "notes": [
            "仮説の確信度は3段階: ★★★=BQデータ断言 / ★★=推測 / ★=推定（必ず明記）",
            "spend < ¥10,000 は除外。スキャン量が少なく統計的に信頼できない",
        ],
        "handson": [],
    },

    "new_slide_kpi_targets": {
        "section": "KPI目標値 & 停止基準",
        "speech": """\
「具体的な数値基準です。必ず覚えてください。

応募CPA目標値:
・¥20,000以下 → 良好（継続・予算引き上げを検討）
・¥20,001〜30,000 → 要観察（クリエイティブ・LP改善を検討）
・¥30,001〜40,000 → 要見直し（CTA配分・ナーチャリング改善）
・¥40,001以上 → 要停止検討

転換率（LINE登録→応募）:
・15%以上 → 良好 / 10〜14% → 要改善 / 10%未満 → 緊急対応

クリエイティブ停止基準:
・消化 ¥15,000超で CV 0件 → 即停止
・出稿2日経過で消化 ¥1,000未満 → 停止

これを月曜のKPIチェック時に毎週確認します。」""",
        "notes": [
            "LINE登録CPA目安: 顕在層 ¥1,500〜3,000 / 潜在層 ¥700〜1,500",
            "停止基準は knowledge/target/Prerequisites/ST_07_KPI評価ルール.md に詳細あり",
        ],
        "handson": [],
    },

    "new_slide_action_flow": {
        "section": "分析 → アクション フロー",
        "speech": """\
「分析してからアクションを取るまでのフローです。
Step 1: BigQueryで直近90日CPA確認（spend ≥ ¥10,000の広告のみ）
Step 2: 停止判断（消化¥15,000超でCV 0件 → 即停止）
Step 3: 予算調整（月10%以上の変更は事前確認必須）
Step 4: 新クリエイティブ企画（create-scenario スキルで起動）
Step 5: LP改善が必要なら lp-copy-variants でコピー案を生成

指標が下がった時のトラブルシューティング:
・CTR低下 → クリエイティブの摩耗 → 訴求軸・動画の型を入れ替え
・CVR低下 → 広告とLPの期待値ギャップ → メッセージ一貫性を確認
・IMP低下 → AIの過度な絞り込み → ターゲット拡張を検討」""",
        "notes": [
            "BigQueryのads-analystエージェントが90日CPA確認を自動でやってくれる",
            "予算変更の承認フロー: 運用管理SSに記録してから変更する",
        ],
        "handson": [
            "1. Claude Codeに「広告分析して」と入力 → ads-analystが直近90日を自動分析",
            "2. 停止候補のリストを確認 → 管理画面で停止操作",
            "3. kpi-report で今週の数値を確認 → 異常があればアクションを取る",
        ],
    },

    "slide12": {
        "section": "チェックリスト ─ 理解度の確認",
        "speech": """\
「チェックリストで理解度を確認しましょう。口頭で答えられるかを確認します。」""",
        "notes": [
            "質問形式で確認すると理解度が把握しやすい",
        ],
        "handson": [
            "Q: ST事業の収益モデルを説明して（掲載課金モデル）",
            "Q: 直近40日のCV数を過小評価として扱う理由は？（タイムラグ40日）",
            "Q: 応募CPAが¥28,000の時、次に何をすべき？（要観察→クリエイティブ・LP改善検討）",
            "Q: クリエイティブの停止基準は？（¥15,000超でCV 0件→即停止）",
            "Q: BigQueryのCV値と管理画面を使い分ける理由は？（ビュースルーCV混在）",
            "Q: kpi-reportスキルを自分で実行してみて",
            "Q: どのスキルをどんな時に使うか3つ言えますか？",
        ],
    },

    "slide13": {
        "section": "まとめ",
        "speech": """\
「この仕事を一言で言うと——
KPIを理解して、クリエイティブとLPでCVRを上げていく仕事です。

わからないことはClaudeに聞けば大体答えてくれます。
ただし、BigQueryのCVはビュースルー混在なので、
最終判断は必ず管理画面の数値で確認してください。

月曜のkpi-reportから始めて、まず1週間のサイクルを一緒に回しましょう。
何かあれば丸山か足立に聞いてください。よろしくお願いします。」""",
        "notes": [
            "重要ドキュメント一覧（付録Aに記載）",
            "足立さんの資料が届いたら付録Bを更新する",
        ],
        "handson": [],
    },
}

# ─────────────────────────────────────────────────────────────────────
# 新井さん向け差し替え台本
# ロジー（KPI体系・分析フレームワーク）は軽く、
# 運用フロー・クリエイティブ作成・スキル活用にウエイト
# ─────────────────────────────────────────────────────────────────────
NARRATION_ARAI = {
    "slide01": {
        "section": "オープニング",
        "speech": """\
「今日はST（塾講師ステーション）のメタ広告運用の全体像をお伝えします。
新井さんはロジカル面はもうご存知だと思うので、
実際の運用フローとクリエイティブ制作の具体的な手順を中心に話します。
後半は、私が使っているClaude Codeのスキルについての相談も時間を取れればと思います。」""",
        "notes": [
            "KPI計算式・ビジネスモデル等は必要なら補足する程度でOK",
            "運用・クリエイティブの具体的な手順の共有に集中する",
        ],
        "handson": [],
    },

    "slide02": {
        "section": "AGENDA",
        "speech": """\
「今日のアジェンダです。
① STの概要（軽く）
② 実際の週次運用フロー（ここを一番厚く）
③ クリエイティブ制作の具体的な流れ（ここも厚く）
④ 使っているツール・Claude Codeスキルの紹介
⑤ スキルの改善相談（時間あれば）」""",
        "notes": [
            "KPIの詳細な説明はスキップ or 「ご存知だと思いますが」と前置きして短縮",
        ],
        "handson": [],
    },

    "slide03": {
        "section": "① ST概要（軽く）",
        "speech": """\
「STはざっくり言うと、塾講師バイトの求人サイトです（大学生向け）。
私たちアフェニティチームの役割は、Meta広告でユーザーをLPに誘導して
LINE登録・応募してもらうことです。

ビジネスモデルは掲載課金なので、採用が増えるほど塾側の満足度が上がります。
この辺はご存知だと思うのでここまでにします。」""",
        "notes": [
            "事業の詳細より『どう運用するか』に早く移行する",
        ],
        "handson": [],
    },

    "slide04": {
        "section": "① ターゲット3ペルソナ（運用への活用方法で説明）",
        "speech": """\
「ターゲットは大学生3種類のペルソナです。ここは運用に直結するので覚えておいてください。
① タイパ重視（積極探し）: スピード感・効率訴求が刺さる → CTRが高い傾向
② 単願（慎重型）: 1社に絞って選びたい → CVRが高い傾向
③ 併願（比較型）: 複数社を比較中 → 競合差別化訴求が有効

実績ベースで言うと、単願 × ブランド診断CTAの組み合わせが今一番CPAが良いです（直近90日）。
クリエイティブを作るとき、まず『どのペルソナに話すか』を決めてから始めます。
1クリエイティブ1ペルソナが鉄則で、複数を詰め込むとCV 0になりやすいです。」""",
        "notes": [
            "直近の勝ちパターン: 単願 × ブランド診断CTA CPA ¥12,310（2026年8月実績）",
            "タイパは CTR が高いが CVR で単願に負けるケースがある（BQ分析済み）",
        ],
        "handson": [],
    },

    "slide05": {
        "section": "② KPI体系（概要のみ）",
        "speech": """\
「KPIツリーはご存知だと思うので要点だけ。
IMP → クリック → LINE登録 → 応募 の流れで、
私たちが直接動かせるのはクリエイティブのCTR と LPのCVR です。

評価の実務ルールだけ押さえてください。
・直近40日以内のCV数は過小評価（応募タイムラグ40日）
・評価は必ず直近90日累計ベース
・spend < 1万円のクリエイティブは評価から除外する」""",
        "notes": [
            "KPIの計算式は knowledge/data/bigquery-schema.md に記載",
            "タイムラグの話は重要なので軽くは触れる",
        ],
        "handson": [],
    },

    "slide06": {
        "section": "② タイムラグ（運用判断への影響）",
        "speech": """\
「タイムラグについてだけ補足します。LINE登録から応募まで中央値40日あります。
実務への影響は一点: 直近4〜6週のCVが少なくても焦らない、ということです。
KPI評価は直近90日累計で見ます。週次の数値は『速度感チェック』にしか使いません。
これを忘れると、まだ評価できない段階でクリエイティブを止める判断ミスが起きます。」""",
        "notes": [
            "タイムラグを知らないと週次が良くない時に誤った停止判断をしてしまう",
        ],
        "handson": [],
    },

    "slide07": {
        "section": "③ 週次ルーティン ─ 実際の運用フロー（詳細）",
        "speech": """\
「週次の運用フローを具体的に説明します。ここが今日のメインです。

■ 月曜（KPIチェック）
1. Claude Codeを開いて「STのKPI報告して 2026/09/01-2026/09/07」と入力
2. 自動でBigQueryからデータ取得 → 4セクション形式のレポートが出てくる
3. 停止候補（spend ≥ ¥15,000 / CV 0件）が自動リストアップされる
4. --write フラグで確認後スプシに書き込み

■ 火〜水（評価・改善）
1. 管理画面で停止候補の広告を実際に停止（BigQueryのCVはビュースルー混在なので必ず管理画面で確認）
2. CTR低下 → クリエイティブ摩耗 → 入れ替えを検討
3. CVR低下 → 広告とLPの訴求ズレ → lp-copy-variantsでFVコピーを見直す

■ 木〜金（クリエイティブ準備）
1. 来週入稿するクリエイティブのシナリオを「シナリオ作って」でClaude Codeに依頼
2. Canvaでクリエイティブを制作（シナリオをそのまま貼り付け）
3. 命名規則チェック → 入稿

■ 月末
1. 翌月のシナリオ設計（create-scenario）
2. 季節変数の確認（knowledge/creative/monthly_seasonal_variables.md）
3. A/Bテストの判定（spend ≥ ¥50,000 / CV ≥ 30件が揃ってから）」""",
        "notes": [
            "月曜のkpi-reportは15〜20分で完結する（スクリプトが全部やってくれる）",
            "管理画面の停止操作だけは手動。BigQueryの停止候補はあくまで参考値",
            "A/Bテスト判定基準: CVR差 +2pt 以上 & spend ≥ ¥50,000 が目安",
        ],
        "handson": [
            "【実際にやってみる】",
            "1. ターミナルで: cd /Users/119322/Desktop/claude-code-template_af",
            "2. Claude Codeを起動",
            "3. 「STのKPI報告して 2026/09/01-2026/09/07」と入力して実行を確認",
            "4. 出力の見方を解説（全体KPI / adset別 / クリエイティブ別 / 停止候補）",
            "5. スプシへの書き込みは --write フラグで（ここは一緒に確認してから）",
        ],
    },

    "slide08": {
        "section": "④ 使用ツール ─ 実際の使い方（重点解説）",
        "speech": """\
「ツールを実際の使い方で説明します。

■ Claude Code（最重要）
チャットで日本語を入力するだけでスキルが起動します。
よく使うのは:
・「STのKPI報告して」→ kpi-report（月曜ルーティン）
・「シナリオを作って」→ create-scenario（クリエイティブ制作）
・「広告分析して」→ ads-analyst（クリエイティブ評価・停止判断）
・「FVのコピーを複数案出して」→ lp-copy-variants（LP改善）
・「Canvaのデザインを直して」→ canva-story-design（デザイン編集）

■ Meta広告管理画面
クリエイティブの停止・予算変更はここで手動操作。
BQの数値と管理画面の数値は必ずここで最終確認する。

■ Canva
create-scenarioで出てきたシナリオをテキストレイヤーに貼り付けるだけ。
チームフォルダにテンプレートがあるので、コピーして編集する。

■ BigQuery
Claude Codeが自動でクエリを書いてくれるので、SQLは書かなくていい。
ただし「ビュースルーCV混在」の問題があるので、CVの実数は管理画面で確認する。」""",
        "notes": [
            "Claude Codeの具体的なコマンド一覧: CLAUDE.md の「キーワード→スキル対応」を参照",
            "BigQuery認証: secrets/token.json が必要（初回設定は setup スキルで）",
        ],
        "handson": [
            "【Claude Code スキルを一通り触ってみる】",
            "1. 「広告分析して」と入力 → ads-analystが直近90日を分析",
            "2. 「FVのコピーバリエーションを出して」と入力 → lp-copy-variantsが起動",
            "3. Canvaを開いてテンプレートフォルダを確認",
        ],
    },

    "slide09": {
        "section": "⑤ LPガイド ─ 運用上のポイント",
        "speech": """\
「LPについては、運用上で押さえるべきポイントだけ話します。

■ 最重要: 広告訴求とFVの一致
広告で「タイパ」訴求していても、LPのFVが「合う塾を探して」だと離脱します。
B2キャンペーン分析でも確認していて、広告とLPの訴求がズレるとCV 0になる事例があります。
クリエイティブを作るとき、そのクリエイティブがどのLPに飛ばすかを先に決める。

■ LP種類
・ペルソナLP: 汎用（どのペルソナにも対応）
・ブランド診断LP: CVRが高い（心理ハードル低い）
・気軽に診断LP: さらに心理ハードル低い

■ 変更するときの注意
変更前に足立さんに確認。FVのコピー変更はA/Bテスト設計が必須。
ペライチ担当に事前連絡してから公開タイミングを合わせる。」""",
        "notes": [
            "LPファイル: lp/line_meta_IG.html（Gitで管理）",
            "FVバリアント作成が残課題（シフト週1〜OK・夏休みだけOK版）",
        ],
        "handson": [],
    },

    "slide10": {
        "section": "⑤ クリエイティブ制作 ─ 実際の制作フロー（詳細）",
        "speech": """\
「クリエイティブ制作の実際の流れを説明します。ここが一番重要です。

■ STEP 1: シナリオ設計（Claude Code）
Claude Codeに「シナリオを作って」と入力すると create-scenario スキルが起動します。
シナリオの構造はこうなっています:
・フック（0〜3秒）: スクロールを止める一言。ペインや問いかけが有効
・ボディ（3〜15秒）: 問題提起 → ST が解決 → 実績で信頼
・CTA（ラスト3秒）: 「LINE登録して」か「適職診断してみて」

■ STEP 2: 命名規則チェック
入稿前に命名規則を必ず確認します（knowledge/creative/meta-ads-naming.md）。
形式: [訴求軸]_[動画の型]_[詳細]_[日付]
例: 02単願_静止画_ブランド診断誘導_260901

■ STEP 3: Canvaで制作
テンプレートフォルダからコピーして、シナリオのテキストを貼り付ける。
フック文言がサムネイルの文字に来るように配置する。

■ STEP 4: 入稿
Meta管理画面で入稿。審査後に配信開始。
新クリエイティブは最初3〜5日でIMP・CTRの初動を確認する。

■ 勝ちパターン（現時点）
・単願訴求 × ブランド診断CTA: CPA ¥12,310（2026年8月）
・静止画でもCVが出る（フック文言が強ければOK）
・1訴求軸に絞る（複数詰め込みはCV 0になりやすい）
・季節変数に合わせる（9月推奨: タイパ35%/単願40%/併願25%）」""",
        "notes": [
            "create-scenario スキルは11ファイルを自動読み込みして生成するので精度が高い",
            "季節変数マスタ: knowledge/creative/monthly_seasonal_variables.md",
            "命名規則マスタ: knowledge/creative/meta-ads-naming.md",
        ],
        "handson": [
            "【create-scenario スキルを実際に動かす】",
            "1. Claude Codeに「10月用のシナリオを作って。単願・ブランド診断・動画3本」と入力",
            "2. 生成されたシナリオを確認（PASONA構成・コンプライアンスチェック済み）",
            "3. Canvaを開いてテンプレートからコピー → テキストレイヤーに貼り付け",
            "4. 命名規則に従って広告名を決める",
            "5. 管理画面で入稿（審査に通るか確認）",
        ],
    },

    "slide11": {
        "section": "⑥ 分析 ─ 停止・継続判断の実務",
        "speech": """\
「分析は『何をアクションに変えるか』に集中して説明します。

■ 月曜のチェックで見るもの
・停止判断: spend ≥ ¥15,000 で CV 0件 → 即停止
・継続判断: CPA が ¥20,000以下 → 予算引き上げを検討
・要観察: ¥20,001〜30,000 → クリエイティブかLPのどちらが問題か特定する

■ CTRが低いとき（クリエイティブ問題）
→ フック文言が弱い。訴求軸か動画の型を変えてシナリオを作り直す

■ CVRが低いとき（LP問題）
→ 広告とLPの訴求がズレていることが多い。lp-copy-variantsでFVコピーを修正する

■ 深掘り分析が必要なとき
→ Claude Codeに「広告分析して」と入力。ads-analystエージェントが自動で90日分を分析して
　 Bootstrap信頼区間・週次トレンド・訴求軸別CPAまで出してくれる」""",
        "notes": [
            "分析フレームワーク（結論→根拠→アクション）は新井さんご存知なのでスキップ可",
            "BigQueryのCV値は参考値。最終確認は管理画面で",
        ],
        "handson": [
            "「広告分析して」と入力してads-analystが何をやるかを実演",
        ],
    },

    "new_slide_kpi_targets": {
        "section": "停止基準 ─ 判断の数値基準（一覧）",
        "speech": """\
「判断基準の数値だけ確認します。
・spend ≥ ¥15,000 / CV 0件 → 即停止
・出稿2日 / 消化 ¥1,000未満 → 停止（配信設定ミスの可能性）
・応募CPA ¥20,000以下 → 良好
・応募CPA ¥30,000超 → 要見直し
・転換率 < 10% → LP緊急対応
これを月曜のkpi-reportの結果と照合して判断します。」""",
        "notes": [
            "数値基準の詳細: knowledge/target/Prerequisites/ST_07_KPI評価ルール.md",
        ],
        "handson": [],
    },

    "new_slide_action_flow": {
        "section": "分析 → アクション フロー（実務手順）",
        "speech": """\
「実際の判断フローを確認します。
Step 1: kpi-reportで直近週の数値を取得（月曜）
Step 2: 停止候補リストを確認 → 管理画面で停止
Step 3: 予算調整（月10%以上の変更は足立さんに確認）
Step 4: 入れ替えシナリオを「シナリオ作って」で生成 → Canvaで制作 → 入稿
Step 5: LP改善が必要なら「FVのコピー案を出して」でlp-copy-variantsを起動

この一連の流れがClaude Codeで完結します。管理画面での実際の停止・入稿操作だけ手動です。」""",
        "notes": [
            "実際の操作は『Claude Codeで分析・生成』→『管理画面で実行』の2ステップ",
        ],
        "handson": [
            "一連のフローを一度通してやってみる（kpi-report → 停止候補確認 → シナリオ生成）",
        ],
    },

    "slide12": {
        "section": "スキル改善の相談",
        "speech": """\
「最後に、現在使っているClaude Codeのスキルについて相談させてください。

■ 現状の課題
1. create-scenario: シナリオ生成まではできるが、その後のCanvaへの流し込みが手動
2. kpi-report: 応募CVにバグがある（BQのcustom_cv_2がLINE登録CVと同値になってしまう）
3. ads-analyst: 分析後のアクション（停止・シナリオ生成）が自動連携できていない

■ 改善したいこと（優先度順）
① kpi-reportの応募数入力を半自動化したい（手動入力をなくしたい）
② 分析→シナリオ生成の流れをワンコマンドでやりたい
③ Canvaへの自動テキスト挿入（Playwright連携）

この辺り、新井さんのご意見をいただけますか？」""",
        "notes": [
            "新井さんの視点から「こういう機能があれば」という要望を聞く時間を設ける",
            "スキル改善のアイデアは .claude/skills/ 配下のMarkdownを直接編集するだけで反映される",
        ],
        "handson": [
            "【スキルファイルを実際に見てもらう】",
            "1. .claude/skills/kpi-report/SKILL.md を開いて構造を説明",
            "2. .claude/skills/create-scenario/SKILL.md を開いて改善余地を確認",
            "3. 「こういう機能がほしい」をその場でSKILL.mdに追記するデモ",
        ],
    },

    "slide13": {
        "section": "まとめ & 次のアクション",
        "speech": """\
「まとめます。
この仕事は『KPIを理解して、クリエイティブとLPでCVRを上げる』仕事です。

Claude Codeがルーティン作業の大半をサポートしてくれるので、
新井さんには特に『クリエイティブの企画・訴求判断』と『LP改善の意思決定』に
集中してもらえると思います。

次のアクションとしては:
① 月曜に一緒にkpi-reportを実行してみる
② 来月用のシナリオをcreate-scenarioで一緒に作る
③ スキル改善の優先順位を決める（今日の話を踏まえて）

何かわからないことはその都度聞いてください。よろしくお願いします。」""",
        "notes": [
            "新井さんがClaudeのスキルをすぐに使えるよう、次回までにtoken.jsonのセットアップを依頼する",
        ],
        "handson": [],
    },
}

# ─────────────────────────────────────────────────────────────────────
# よくある質問（付録）
# ─────────────────────────────────────────────────────────────────────
FAQ = [
    ("BigQueryとは何ですか？",
     "広告データが自動的に集まるGoogleのデータベース。複数のキャンペーン・広告の数値を一括で分析できる。毎日更新されるが、管理画面より1日程度遅延することがある。"),
    ("ビュースルーCVとは？",
     "広告を見たけどタップしなかった人が、後で別の経路でLINE登録した場合のCV。Metaは『広告を見た影響』と判定してカウントするが、本当に広告の効果かどうかは不明。信頼性が低いため、管理画面の『クリックスルーCV』が実態に近い。"),
    ("月間予算の変更はどうすればいい？",
     "月間目標の±10%以内なら自分で変更OK。10%以上の変更は事前に足立さんに確認が必要。運用管理SSに記録してから変更する。"),
    ("新しいクリエイティブはどうやって作る？",
     "Claude Codeに「シナリオを作って」と言えばcreate-scenarioスキルが起動する。シナリオをCanvaに貼り付けて制作。1シーズン各キャンペーンに5本が目安。"),
    ("LPを変更したい場合は？",
     "lp/line_meta_IG.html を編集してGitでバージョン管理。変更前に足立さんに確認を取ること。FVのコピー変更はA/Bテスト設計が必要。ペライチ担当に事前連絡必須。"),
    ("kpi-reportスキルでエラーが出た場合は？",
     "まず python3 scripts/kpi/kpi_report_st.py --list-adsets で adset名を確認する。TOKEN_FILEが secrets/token.json にあるか確認。期限切れなら python3 scripts/utils/reauth_google.py で再認証する。"),
]

# ─────────────────────────────────────────────────────────────────────
# Google Slides API でスライド内容を取得
# ─────────────────────────────────────────────────────────────────────

def extract_slide_texts(slide: dict) -> list[str]:
    """スライドからテキストを抽出（重複除去）"""
    texts = []
    seen = set()
    for elem in slide.get("pageElements", []):
        tf = elem.get("shape", {}).get("text", {})
        for te in tf.get("textElements", []):
            content = te.get("textRun", {}).get("content", "").strip()
            if content and content != '\n' and content not in seen:
                texts.append(content)
                seen.add(content)
    return texts


def build_doc_text(slides: list, target: str = "岩崎") -> str:
    """台本テキストを組み立てる"""
    import datetime
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    narr_dict = NARRATION_ARAI if target == "新井" else NARRATION
    lines = []

    if target == "新井":
        lines.append("新井さん向け オンボーディング台本（メタ広告運用）\n")
        lines.append(f"担当: 丸山大輝  |  作成: {today_str}\n")
        lines.append("【ポイント】ロジー・KPI体系は軽く。運用フロー・クリエイティブ制作・スキル活用にウエイト。\n")
    else:
        lines.append("岩崎さん向け オンボーディング台本（メタ広告運用）\n")
        lines.append(f"担当: 丸山大輝  |  作成: {today_str}  |  対象: 10月以降\n")
    lines.append(f"ベーススライド: https://docs.google.com/presentation/d/{PRES_ID}/edit\n")
    lines.append("\n")
    lines.append("【この台本の使い方】\n")
    lines.append("・スライド番号に対応してセクションが並んでいる\n")
    lines.append("・「口頭説明」がそのまま話す文言（読み上げでOK）\n")
    lines.append("・「補足知識」は質問が来た時に答える内容\n")
    lines.append("・「ハンズオン」は実際に一緒にやる操作手順\n")
    if target == "新井":
        lines.append("・スライド12（スキル改善の相談）は最後に時間を設ける\n")
    else:
        lines.append("・足立さんの資料が届いた後に★マーク箇所を追記・更新する\n")
    lines.append("\n")
    lines.append("【事前確認チェック（レクチャー前にやっておくこと）】\n")
    lines.append("□ Claude Codeのインストール確認（claude --version で起動確認）\n")
    lines.append("□ secrets/token.json の配置確認（OAuth認証済みファイル）\n")
    lines.append("□ BigQueryのプロジェクトアクセス権確認（bigquery-jukust）\n")
    lines.append("□ Meta広告管理画面へのアクセス権確認\n")
    lines.append("□ kpi-reportスキルの試走確認（事前に自分で実行しておく）\n")
    lines.append("\n")
    lines.append("━" * 60 + "\n\n")

    for i, slide in enumerate(slides):
        slide_id = slide.get("objectId", "")
        narr = narr_dict.get(slide_id, {})
        slide_texts = extract_slide_texts(slide)

        # セクション見出し
        section = narr.get("section", f"スライド {i+1}")
        lines.append(f"▼ スライド{i+1:02d}: {section}  (ID: {slide_id})\n")
        lines.append("\n")

        # 実際のスライド内容を参照として表示（先頭5行まで）
        if slide_texts:
            lines.append("[スライド本文（参照）]\n")
            for t in slide_texts[:5]:
                lines.append(f"  {t}\n")
            if len(slide_texts) > 5:
                lines.append(f"  ... 他{len(slide_texts)-5}件\n")
            lines.append("\n")

        # 口頭説明
        speech = narr.get("speech", "")
        if speech:
            lines.append("【口頭説明】\n")
            for sline in speech.strip().split('\n'):
                lines.append(f"{sline}\n")
            lines.append("\n")

        # 補足知識
        notes = narr.get("notes", [])
        if notes:
            lines.append("【補足知識】\n")
            for note in notes:
                lines.append(f"  ・{note}\n")
            lines.append("\n")

        # ハンズオン
        handson = narr.get("handson", [])
        if handson:
            lines.append("【ハンズオン手順】\n")
            for step in handson:
                lines.append(f"  {step}\n")
            lines.append("\n")

        lines.append("─" * 60 + "\n\n")

    # 付録A: よくある質問
    lines.append("【付録A: よくある質問 & 答え】\n\n")
    for q, a in FAQ:
        lines.append(f"Q: {q}\n")
        lines.append(f"A: {a}\n\n")

    # 付録B: スキル改善案（新井さん向けのみ）
    if target == "新井":
        lines.append("━" * 60 + "\n\n")
        lines.append("【付録B: 現状スキルの改善案（相談メモ）】\n\n")
        improvements = [
            ("① kpi-report", "改善優先度: 高",
             [
                 "現状の問題: 応募CV（custom_cv_2）がLINE登録CVと同値になるBQバグがある → 応募数は手動入力",
                 "改善案1: kpi-reportに『今週の応募数は？』の対話入力フローを追加し、手動入力をスクリプト内で記録",
                 "改善案2: 週次レポートに『先週比』の差分（↑↓）と変化率を自動表示",
                 "改善案3: CPA前週比150%超でアラートメッセージを追加（異常値の早期検知）",
             ]),
            ("② create-scenario", "改善優先度: 高",
             [
                 "現状の問題: シナリオ生成まではできるが、Canvaへの流し込みが手動（コピペ作業が残る）",
                 "改善案1: ads-analystの分析結果（勝ちパターン）を自動でcreate-scenarioに渡す連携を実装",
                 "改善案2: Playwright（web-autopilotスキル）でCanvaを自動操作し、シナリオテキストをテキストレイヤーに直接挿入",
                 "改善案3: シナリオ生成後に『命名規則候補』を自動提示（入稿前の確認工数を削減）",
             ]),
            ("③ ads-analyst", "改善優先度: 中",
             [
                 "現状の問題: 分析後のアクション（停止・シナリオ生成）が手動分離している",
                 "改善案1: 分析完了後に『停止候補リスト』を管理画面用フォーマット（広告ID付き）で出力",
                 "改善案2: Bootstrap統計（95%CI・置換検定）を標準機能として組み込む（lpo_ab_insights.pyを統合）",
                 "改善案3: 分析→『勝ちパターンを横展開するシナリオを作って』の自動引き継ぎフロー",
             ]),
            ("④ 新規スキル提案: creative-lifecycle", "改善優先度: 中",
             [
                 "概要: クリエイティブの『疲弊度』を週次で自動チェックし、入れ替えタイミングを提案",
                 "仕組み: BQで広告の運用日数 vs CPA の回帰分析 → 疲弊傾向を検知",
                 "出力: 『入れ替え推奨クリエイティブリスト』＋『代替シナリオの方向性』",
                 "実装: lpo_ab_insights.pyのライフサイクル分析部分をkpi-reportに統合するだけ",
             ]),
            ("⑤ 新規スキル提案: lp-ab-tracker", "改善優先度: 低",
             [
                 "概要: A/Bテストの進捗を自動追跡し、判定基準達成時に通知",
                 "仕組み: BQでA/BのCVR差を週次で監視 → spend≥¥50,000 & CV≥30件 で自動判定",
                 "出力: 『今週のA/Bテスト状況』をKPIレポートに追加",
             ]),
        ]
        for skill, priority, items in improvements:
            lines.append(f"■ {skill}  [{priority}]\n")
            for item in items:
                lines.append(f"  ・{item}\n")
            lines.append("\n")
        lines.append("【スキル改善の実装方法】\n")
        lines.append("・各スキルは .claude/skills/{スキル名}/SKILL.md を編集するだけで動作が変わる\n")
        lines.append("・Pythonスクリプトの追加は scripts/kpi/ または scripts/analysis/ に配置\n")
        lines.append("・新規スキルの追加は .claude/skills/{新スキル名}/SKILL.md を新規作成するだけ\n\n")

    # 付録C（新井）/ 付録B（岩崎）: 重要ドキュメント一覧
    appendix_label = "C" if target == "新井" else "B"
    lines.append("━" * 60 + "\n\n")
    lines.append(f"【付録{appendix_label}: 重要ドキュメント・ファイル一覧】\n\n")
    refs = [
        ("オンボーディングスライド",
         f"https://docs.google.com/presentation/d/{PRES_ID}/edit"),
        ("ST_KPI報告スプシ",
         "https://docs.google.com/spreadsheets/d/1xXeCl4Xbkxz-w_jT49TmA3-voruL2cTbF1f308hZ5vQ/edit"),
        ("B2キャンペーン分析レポート",
         "https://docs.google.com/document/d/1ttgYAe6sJDIMft9hOw_mDlStyfu9PClsrQi9Lb1oOns/edit"),
        ("ST広告分析レポート（直近90日）",
         "https://docs.google.com/document/d/1dU3HeHATj-Ee2TAAez67I7zz7HQ_uezsl12O64cC5KI/edit"),
        ("深掘り分析レポート（Bootstrap統計）",
         "https://docs.google.com/document/d/1qGopNUkyKih3ra16-MzUMJgzWpzx2LTg4BnwTrTki3s/edit"),
        ("Claude Codeプロジェクト（ローカル）",
         "/Users/119322/Desktop/claude-code-template_af"),
        ("LP管理ファイル",
         "lp/line_meta_IG.html（Gitで管理）"),
    ]
    for label, url in refs:
        lines.append(f"  ・{label}: {url}\n")

    return "".join(lines)


# ─────────────────────────────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────────────────────────────

print("認証中...")
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

slides_svc = build("slides", "v1", credentials=creds, cache_discovery=False)
docs_svc   = build("docs",   "v1", credentials=creds, cache_discovery=False)

print(f"スライド取得中: {PRES_ID}")
pres   = slides_svc.presentations().get(presentationId=PRES_ID).execute()
slides = pres.get("slides", [])
print(f"  → {len(slides)} 枚のスライドを取得")

print(f"台本テキスト組み立て中... [ターゲット: {TARGET}]")
full_text = build_doc_text(slides, target=TARGET)
print(f"  → {len(full_text):,} 文字")

import datetime
today = datetime.datetime.now().strftime('%Y-%m-%d')
target_label = "新井さん向け" if TARGET == "新井" else "岩崎さん向け"
print("Google Docを作成中...")
doc = docs_svc.documents().create(body={
    "title": f"{target_label} オンボーディング台本（メタ広告・{today}）"
}).execute()
DOC_ID = doc["documentId"]
print(f"  ドキュメント作成: https://docs.google.com/document/d/{DOC_ID}/edit")

docs_svc.documents().batchUpdate(
    documentId=DOC_ID,
    body={"requests": [
        {"insertText": {"location": {"index": 1}, "text": full_text}}
    ]},
).execute()
print("テキスト挿入完了")
time.sleep(1)

title_end = full_text.index('\n') + 1
docs_svc.documents().batchUpdate(
    documentId=DOC_ID,
    body={"requests": [
        {
            "updateParagraphStyle": {
                "range": {"startIndex": 1, "endIndex": title_end},
                "paragraphStyle": {"namedStyleType": "HEADING_1"},
                "fields": "namedStyleType",
            }
        },
        {
            "updateTextStyle": {
                "range": {"startIndex": 1, "endIndex": len(full_text)},
                "textStyle": {"weightedFontFamily": {"fontFamily": "Noto Sans JP"}},
                "fields": "weightedFontFamily",
            }
        },
    ]},
).execute()
print("スタイル適用完了")

url = f"https://docs.google.com/document/d/{DOC_ID}/edit"
print(f"\n完成URL: {url}")
