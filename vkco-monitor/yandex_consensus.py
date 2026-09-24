from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from html import unescape
from typing import Any
from zoneinfo import ZoneInfo

SOURCE_URL = "https://yandex.ru/finance/quote/moex/vkco"
MOSCOW = ZoneInfo("Europe/Moscow")

def _num(value: str) -> float:
    return float(value.replace("\u00a0", "").replace(" ", "").replace(",", ".").replace("₽", "").replace("%", ""))

def _plain(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()

def parse_consensus(html: str, observed_at: str | None = None) -> dict[str, Any]:
    text = _plain(html)
    # Yandex Finance Russian labels. Fail closed if the aggregate target or vote split is absent.
    target_m = re.search(r"([0-9][0-9\\s]*(?:[,.][0-9]+)?)\\s*₽\\s*[+-]?[0-9]+(?:[,.][0-9]+)?%", text, re.I)
    votes_m = re.search(r"(\d+)\s*Продавать\s+(\d+)\s*Держать\s+(\d+)\s*Покупать", text, re.I)
    if not target_m or not votes_m:
        raise ValueError("YANDEX_CONSENSUS_NOT_FOUND")
    sell, hold, buy = map(int, votes_m.groups())
    target = _num(target_m.group(1))
    range_m = re.search(r"От\s*([0-9][0-9\s]*(?:[,.][0-9]+)?)\s*₽.*?Макс\s*([0-9][0-9\s]*(?:[,.][0-9]+)?)\s*₽", text, re.I)
    updated_m = re.search(r"Обновлено\s+([^|]{3,40}?)(?=\s+(?:Мнения аналитиков|Сейчас|От\s|$))", text, re.I)
    out: dict[str, Any] = {
        "status": "OK",
        "source": "Yandex Finance",
        "source_url": SOURCE_URL,
        "observed_at": observed_at or datetime.now(MOSCOW).isoformat(),
        "consensus_target": target,
        "buy": buy,
        "hold": hold,
        "sell": sell,
        "analyst_count": buy + hold + sell,
    }
    if range_m:
        out["target_low"] = _num(range_m.group(1))
        out["target_high"] = _num(range_m.group(2))
    if updated_m:
        out["source_updated_label"] = updated_m.group(1).strip()
    return out

def fetch_consensus(timeout: int = 15) -> dict[str, Any]:
    req = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; VKCO-Control-Room/1.0)",
            "Accept-Language": "ru-RU,ru;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
        return parse_consensus(html)
    except Exception as exc:
        return {
            "status": "DATA_UNAVAILABLE",
            "source": "Yandex Finance",
            "source_url": SOURCE_URL,
            "observed_at": datetime.now(MOSCOW).isoformat(),
            "error": type(exc).__name__,
        }

if __name__ == "__main__":
    print(json.dumps(fetch_consensus(), ensure_ascii=False, sort_keys=True))
