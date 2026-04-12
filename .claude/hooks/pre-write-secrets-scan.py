#!/usr/bin/env python3
"""
PreToolUse hook (Write|Edit): ファイル書き込み前にシークレットのハードコードを検出してブロックする。
"""
import json, sys, re, subprocess, os

PATTERNS = [
    (r'sk-[A-Za-z0-9]{20,}', "OpenAI/Anthropic APIキー"),
    (r'ya29\.[A-Za-z0-9\-_]{20,}', "Google OAuthアクセストークン"),
    (r'AIza[A-Za-z0-9\-_]{30,}', "Google APIキー"),
    (r'"token"\s*:\s*"[A-Za-z0-9\-_\.]{40,}"', "トークン文字列"),
    (r'api_key\s*=\s*["\'][^"\']{10,}["\']', "api_key ハードコード"),
    (r'access_token\s*=\s*["\'][^"\']{20,}["\']', "access_token ハードコード"),
    (r'client_secret\s*=\s*["\'][^"\']{10,}["\']', "client_secret ハードコード"),
]

# __file__ ベースで動的にパスを解決（ポータブル）
ALERT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts', 'security_alert.py')

def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input", {})

        # Write: content フィールド / Edit: new_string フィールド
        content = tool_input.get("content", "") or tool_input.get("new_string", "")
        file_path = tool_input.get("file_path", "")

        # secrets/ フォルダ内は対象外（token.jsonなど正規ファイル）
        if "secrets" in file_path.replace("\\", "/"):
            print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
            return

        for pattern, label in PATTERNS:
            if re.search(pattern, content):
                msg = f"【セキュリティブロック】{label} と思われる文字列を検出しました。\n環境変数または secrets/token.json から読み込む方式に変更してください。"
                # security_alert.py が存在すれば実行
                try:
                    subprocess.Popen(
                        ["python", ALERT_SCRIPT, f"【PreWriteHook】{label}を検出: {file_path}"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass
                print(json.dumps({
                    "hookSpecificOutput": {
                        "permissionDecision": "deny",
                        "permissionDecisionReason": msg
                    }
                }))
                return

        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))

    except Exception:
        # エラー時は通過させる（書き込みをブロックしない）
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))

if __name__ == "__main__":
    main()
