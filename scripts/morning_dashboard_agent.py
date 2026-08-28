from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright

REGISTRY_PATH = Path("config/dashboard_registry.json")
SCREENSHOT_DIR = Path("artifacts/morning_dashboards")
TIMEZONE = ZoneInfo("Europe/Moscow")


def telegram_send_message(token: str, chat_id: str, text: str) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    response.raise_for_status()


def telegram_send_photo(token: str, chat_id: str, image_path: Path, caption: str) -> None:
    with image_path.open("rb") as image_file:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": image_file},
            timeout=60,
        )
    response.raise_for_status()


def capture_dashboard(page, project_name: str, dashboard_url: str, output_path: Path) -> None:
    page.goto(dashboard_url, wait_until="domcontentloaded", timeout=60_000)
    try:
        page.wait_for_load_state("networkidle", timeout=30_000)
    except Exception:
        pass
    time.sleep(5)
    page.screenshot(path=str(output_path), full_page=False)


def load_registry() -> list[dict]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        return 2

    dashboards = [item for item in load_registry() if item.get("enabled") is True]
    if not dashboards:
        print("No enabled dashboards found")
        return 0

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    success = 0
    failed: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page = context.new_page()

        for dashboard in dashboards:
            name = dashboard["project_name"]
            url = dashboard["dashboard_url"]
            safe_name = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
            output_path = SCREENSHOT_DIR / f"{safe_name}.png"
            last_error: Exception | None = None

            for attempt in (1, 2):
                try:
                    capture_dashboard(page, name, url, output_path)
                    now = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M MSK")
                    caption = f"📊 {name}\n🕒 Обновлено: {now}\n\n🔗 Открыть дашборд: {url}"
                    telegram_send_photo(token, chat_id, output_path, caption)
                    success += 1
                    last_error = None
                    print(f"PASS {name} attempt={attempt}")
                    break
                except Exception as exc:
                    last_error = exc
                    print(f"ERROR {name} attempt={attempt}: {exc}", file=sys.stderr)
                    if attempt == 1:
                        time.sleep(3)

            if last_error is not None:
                failed.append(name)
                try:
                    telegram_send_message(token, chat_id, f"⚠️ {name}\nDashboard unavailable")
                except Exception as exc:
                    print(f"ERROR sending failure notification for {name}: {exc}", file=sys.stderr)

        browser.close()

    summary = [
        "✅ Morning Dashboard Agent",
        "",
        f"Успешно: {success}/{len(dashboards)}",
        f"Ошибок: {len(failed)}",
    ]
    if failed:
        summary.append("")
        summary.extend(f"⚠️ {name}" for name in failed)

    telegram_send_message(token, chat_id, "\n".join(summary))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
