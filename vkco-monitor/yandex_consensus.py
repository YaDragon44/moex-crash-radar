from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from html import unescape
from typing import Any
from zoneinfo import ZoneInfo

SOURCE_URL = "https://yandex.ru/finance/quote/moex/vkco"
FALLBACK_URL = "https://etpinvest.ru/quote/vkco/forecast/"
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

def parse_etpinvest(html: str, observed_at: str | None = None) -> dict[str, Any]:
    text=_plain(html)
    target_m=re.search(r"средняя целевая цена\s*₽?\s*([0-9]{2,4}(?:[,.][0-9]+)?)",text,re.I)
    votes_m=re.search(r"Из\s+([0-9]+)\s+аналитиков:\s*([0-9]+)\s+покупать,\s*([0-9]+)\s+держать,\s*([0-9]+)\s+продавать",text,re.I)
    range_m=re.search(r"Диапазон прогнозов:\s*от\s*₽?\s*([0-9]{2,4}(?:[,.][0-9]+)?).*?до\s*₽?\s*([0-9]{2,4}(?:[,.][0-9]+)?)",text,re.I)
    if not target_m or not votes_m: raise ValueError("ETPINVEST_CONSENSUS_NOT_FOUND")
    total,buy,hold,sell=map(int,votes_m.groups())
    if total != buy+hold+sell: raise ValueError("ETPINVEST_CONSENSUS_INCONSISTENT")
    out={"status":"OK","source":"ETP Invest","source_url":FALLBACK_URL,"observed_at":observed_at or datetime.now(MOSCOW).isoformat(),"consensus_target":_num(target_m.group(1)),"buy":buy,"hold":hold,"sell":sell,"analyst_count":total,"analysts":[],"source_mode":"fallback"}
    if range_m: out.update(target_low=_num(range_m.group(1)),target_high=_num(range_m.group(2)))
    return out

def _fetch(url: str, timeout: int) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; VKCO-Control-Room/1.0)","Accept-Language":"ru-RU,ru;q=0.9"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read().decode("utf-8",errors="replace")

def fetch_consensus(timeout: int = 15) -> dict[str, Any]:
    yandex_error=None
    try:
        return parse_consensus(_fetch(SOURCE_URL,timeout))
    except Exception as exc:
        yandex_error=type(exc).__name__
    try:
        out=parse_etpinvest(_fetch(FALLBACK_URL,timeout))
        out.update(primary_source="Yandex Finance",primary_source_url=SOURCE_URL,primary_source_status="DATA_UNAVAILABLE",primary_source_error=yandex_error)
        return out
    except Exception as exc:
        return {"status":"DATA_UNAVAILABLE","source":"Analyst consensus","source_url":SOURCE_URL,"fallback_url":FALLBACK_URL,"observed_at":datetime.now(MOSCOW).isoformat(),"error":type(exc).__name__,"primary_source_error":yandex_error}

if __name__ == "__main__":
    print(json.dumps(fetch_consensus(), ensure_ascii=False, sort_keys=True))
