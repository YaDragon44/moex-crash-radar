from __future__ import annotations

import html
import re
from typing import Any
import requests

URL = "https://vk.company.ru/ru/investors/info/"
RU_MONTHS = "января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря"
DATE_RE = re.compile(r"\b(\d{1,2})\s+("+RU_MONTHS+r")\s+(20\d{2})\b", re.I)


def _text(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.I|re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def parse_latest(raw: str, limit: int = 3) -> list[dict[str, str]]:
    """Extract only dated official VK IR snippets; never invent a title."""
    plain = _text(raw)
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in DATE_RE.finditer(plain):
        date = m.group(0)
        snippet = plain[m.end():m.end()+360].strip(" —–|")
        snippet = re.split(r"\b\d{1,2}\s+(?:"+RU_MONTHS+r")\s+20\d{2}\b", snippet, maxsplit=1, flags=re.I)[0].strip()
        if not snippet or date+"|"+snippet[:100] in seen:
            continue
        seen.add(date+"|"+snippet[:100])
        out.append({"date": date, "text": snippet[:240], "source": "VK IR", "source_url": URL})
        if len(out) >= limit:
            break
    return out


def fetch_latest(limit: int = 3) -> dict[str, Any]:
    try:
        r=requests.get(URL,headers={"User-Agent":"VKCO-Monitor/1.8"},timeout=20)
        r.raise_for_status()
        items=parse_latest(r.text,limit)
        if not items:
            raise ValueError("No dated VK IR items")
        return {"status":"OK","source":"VK IR","source_url":URL,"items":items}
    except Exception as exc:
        return {"status":"DATA_UNAVAILABLE","source":"VK IR","source_url":URL,"items":[],"error":type(exc).__name__}
