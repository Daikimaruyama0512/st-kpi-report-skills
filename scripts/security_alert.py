import os
import requests
import json
import sys

def load_env(file_path):
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                env_vars[key] = val
    return env_vars

def send_slack_alert(message, env_vars):
    webhook_url = env_vars.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL not found in .env")
        return

    payload = {
        "text": f"*ハードコード検知アラート*\n{message}",
        "channel": env_vars.get("SLACK_CHANNEL"),
        "username": env_vars.get("SLACK_BOT_NAME", "Claude Security"),
        "icon_emoji": env_vars.get("SLACK_ICON_EMOJI", ":warning:")
    }

    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            print("Slack alert sent successfully.")
        else:
            print(f"Failed to send Slack alert: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending Slack alert: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python security_alert.py <message>")
        sys.exit(1)

    alert_message = sys.argv[1]
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = load_env(os.path.join(project_root, ".env"))
    send_slack_alert(alert_message, env)
