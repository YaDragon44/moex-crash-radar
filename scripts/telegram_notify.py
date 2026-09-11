#!/usr/bin/env python3
"""Send a prepared monitoring message to Telegram.

Required env vars:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID

Message source (first available):
  MONITOR_MESSAGE env var
  --file <path>

This module contains no trading logic. It is transport only.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def load_message(path: str | None) -> str:
    env_message = os.getenv("MONITOR_MESSAGE", "").strip()
    if env_message:
        return env_message
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="UTF-8 text file containing the prepared monitor message")
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    message = load_message(args.file)

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set", file=sys.stderr)
        return 2
    if not chat_id:
        print("ERROR: TELEGRAM_CHAT_ID is not set", file=sys.stderr)
        return 2
    if not message:
        print("ERROR: no monitor message supplied", file=sys.stderr)
        return 2

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message[:4096],
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"ERROR: Telegram request failed: {exc}", file=sys.stderr)
        return 1

    if not payload.get("ok"):
        print(f"ERROR: Telegram API returned: {payload}", file=sys.stderr)
        return 1

    print("Telegram notification sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
