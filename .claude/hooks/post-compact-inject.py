#!/usr/bin/env python3
"""
PostCompact hook: コンテキスト圧縮後に重要ルールを再注入する。
stdout に出力した文字列が Claude の次のコンテキストに追加される。
"""
import json, sys

def main():
    try:
        json.load(sys.stdin)  # stdin を消費する（必須）
    except Exception:
        pass

    reminder = """【コンテキスト再注入】
- シークレット（APIキー・トークン）のハードコード禁止。TOKEN_FILE = secrets/token.json を使う
- 分析の出力は「結論 → データ → アクション3件以内」の順
- .claude/ 配下を触るときは claude-code-best-practice/ の対応ドキュメントを先に読む
- スプシ・カレンダー書き込み前は1行確認を取る（明示的指示があれば即実行）
"""
    print(reminder)

if __name__ == "__main__":
    main()
