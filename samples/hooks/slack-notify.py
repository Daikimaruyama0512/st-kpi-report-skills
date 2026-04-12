#!/usr/bin/env python3
"""
===== サンプル: Stop hook — Claudeの応答をSlackに送信 =====
「スラックで送って」とユーザーが言った場合に、Claudeの最後の応答をSlackに転送する。
そのままでは動きません。.env にSLACK_WEBHOOK_URLを設定してください。
"""
import json
import os
import sys
import urllib.request

# __file__ ベースで .env を解決（ポータブル）
def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    env_path = os.path.abspath(env_path)
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()
WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
CHANNEL = os.environ.get("SLACK_CHANNEL", "")
BOT_NAME = os.environ.get("SLACK_BOT_NAME", "Claude")


def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif "text" in block:
                    texts.append(block["text"])
        return "\n".join(t for t in texts if t)
    return ""


def main():
    try:
        data = json.load(sys.stdin)
        transcript_path = data.get("transcript_path", "")
        if not transcript_path:
            return

        messages = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except Exception:
                        pass

        # ユーザーの最後のメッセージを取得
        last_user_text = ""
        for msg in reversed(messages):
            role = msg.get("role") or msg.get("type", "")
            if role == "user":
                last_user_text = extract_text(msg.get("content", ""))
                break

        # トリガーワードが含まれていなければ何もしない
        if "スラックで送って" not in last_user_text:
            return

        # Claudeの最後の応答を取得
        last_assistant_text = ""
        for msg in reversed(messages):
            role = msg.get("role") or msg.get("type", "")
            if role == "assistant":
                last_assistant_text = extract_text(msg.get("content", ""))
                if last_assistant_text:
                    break

        if not last_assistant_text or not WEBHOOK_URL:
            return

        payload = json.dumps({
            "channel": CHANNEL,
            "text": last_assistant_text,
            "username": BOT_NAME,
        }).encode("utf-8")

        req = urllib.request.Request(
            WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)

    except Exception:
        pass


if __name__ == "__main__":
    main()
