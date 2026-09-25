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
    votes_m = re.search(r"(\d+)\s*Продавать\s+(\d+)\s*Держать\s+(\d+)\s*Покупать", text, re.I)
    if not votes_m:
        raise ValueError("YANDEX_CONSENSUS_NOT_FOUND")
    # Anchor target extraction to the analyst-consensus neighborhood, never to
    # an arbitrary RUB amount elsewhere on the dynamic quote page.
    # Aggregate target belongs before the vote split; analyst rows belong after it.
    # Prefer an explicit forecast heading when present, otherwise use the last
    # price/upside pair before the votes.
    before=text[max(0, votes_m.start()-1200):votes_m.start()]
    headed=re.search(r"(?:Прогноз цены|Средняя цена|Консенсус[^0-9]{0,80})(\d{2,4}(?:[,.]\d+)?)\s*₽\s*([+-][0-9]+(?:[,.][0-9]+)?)%", before, re.I)
    candidates=list(re.finditer(r"(\d{2,4}(?:[,.]\d+)?)\s*₽\s*([+-][0-9]+(?:[,.][0-9]+)?)%", before, re.I))
    target_m=headed or (candidates[-1] if candidates else None)
    if target_m is None:
        raise ValueError("YANDEX_CONSENSUS_TARGET_NOT_FOUND")
    sell, hold, buy = map(int, votes_m.groups())
    target = _num(target_m.group(1))
    upside = _num(target_m.group(2))
    # Sanity-check the pair. A broken/dynamic page must fail closed rather than
    # publish a plausible-looking but wrong analyst target.
    if target <= 0 or abs(upside) > 1000:
        raise ValueError("YANDEX_CONSENSUS_TARGET_INVALID")
    range_m = re.search(r"От\s*([0-9][0-9\s]*(?:[,.][0-9]+)?)\s*₽.*?Макс\s*([0-9][0-9\s]*(?:[,.][0-9]+)?)\s*₽", text, re.I)
    updated_m = re.search(r"Обновлено\s+([^|]{3,40}?)(?=\s+(?:Мнения аналитиков|Сейчас|От\s|$))", text, re.I)
    analyst_text = text[votes_m.end():]
    analyst_re = re.compile(
        r"([А-ЯA-ZЁ][А-Яа-яA-Za-zЁё0-9 .&+\-]{1,70}?)\s+"
        r"Прогноз до ([0-9]{1,2} [А-Яа-яё]+ [0-9]{4})\s+"
        r"(Покупать|Держать|Продавать)\s+"
        r"([0-9]{1,4}(?:[,.][0-9]+)?)\s*₽\s*"
        r"([+-][0-9]+(?:[,.][0-9]+)?%)",
        re.I,
    )
    analysts = [
        {
            "name": m.group(1).strip(),
            "forecast_to": m.group(2).strip(),
            "recommendation": m.group(3).capitalize(),
            "target": _num(m.group(4)),
            "upside_pct": _num(m.group(5)),
        }
        for m in analyst_re.finditer(analyst_text)
    ]
    out: dict[str, Any] = {
        "status": "OK",
        "source": "Yandex Finance",
        "source_url": SOURCE_URL,
        "observed_at": observed_at or datetime.now(MOSCOW).isoformat(),
        "consensus_target": target,
        "consensus_upside_pct": upside,
        "buy": buy,
        "hold": hold,
        "sell": sell,
        "analyst_count": buy + hold + sell,
        "analysts": analysts,
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
