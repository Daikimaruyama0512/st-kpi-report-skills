#!/usr/bin/env python3
"""
===== サンプル: Notification hook — Claudeの状態をSlackに通知 =====
Claude が入力待ち（idle）や権限確認（permission_prompt）になったときにSlack通知する。
そのままでは動きません。.env にSLACK_WEBHOOK_URLを設定してください。
"""
import json, sys, os, urllib.request

# __file__ ベースで .env を解決（ポータブル）
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()
WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
CHANNEL = os.environ.get("SLACK_CHANNEL", "")
BOT_NAME = os.environ.get("SLACK_BOT_NAME", "Claude Code")

NOTIFY_TYPES = {"idle_prompt", "permission_prompt"}

MESSAGES = {
    "idle_prompt": "Claude が入力待ちです",
    "permission_prompt": "Claude が権限確認を求めています",
}

def main():
    try:
        data = json.load(sys.stdin)
        notification_type = data.get("notification_type", "")

        if notification_type not in NOTIFY_TYPES:
            return
        if not WEBHOOK_URL:
            return

        message = data.get("message", "")
        text = MESSAGES.get(notification_type, "Claude から通知")
        if message:
            text += f"\n>{message}"

        payload_dict = {
            "text": text,
            "username": BOT_NAME,
        }
        if CHANNEL:
            payload_dict["channel"] = CHANNEL
        payload = json.dumps(payload_dict).encode("utf-8")

        req = urllib.request.Request(
            WEBHOOK_URL, data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)

    except Exception:
        pass

if __name__ == "__main__":
    main()
