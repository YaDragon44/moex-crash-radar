"""Kira public portfolio: transcript -> portfolio change candidates.

R0.3 deliberately separates ASR from semantic parsing. The parser never invents
asset, quantity, price or amount. Missing fields stay None and evidence is kept.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Iterable


@dataclass(frozen=True)
class TranscriptSegment:
    start_s: float
    end_s: float
    text: str


@dataclass(frozen=True)
class PortfolioChange:
    action: str
    asset: str | None
    quantity: float | None
    price: float | None
    amount: float | None
    evidence_text: str
    start_s: float
    end_s: float
    confidence: float
    source_url: str


ACTION_PATTERNS = {
    "SELL": (r"\bпрода(?:ю|ла|ём|ем)\b", r"\bзакрыва(?:ю|ла|ем)\b"),
    "REDUCE": (r"\bсокраща(?:ю|ла|ем)\b", r"\bчастичн\w* прода\w*\b"),
    "ADD": (r"\bдокупа(?:ю|ла|ем)\b", r"\bусредня(?:ю|ла|ем)\b"),
    "BUY": (r"\bпокупа(?:ю|ла|ем)\b", r"\bберу\b"),
}

# Conservative aliases: one issuer's stock and bond must not share an alias.
ASSET_ALIASES = {
    "OZON": ("ozon", "озон"),
    "OZPH": ("озон фармацевтика", "ozon фармацевтика", "ozon pharma"),
    "SBER": ("сбер", "сбербанк"),
    "HEAD": ("headhunter", "хэдхантер", "хедхантер"),
    "YDEX": ("яндекс", "yandex"),
    "X5": ("x5", "икс 5", "икс пять"),
    "RENI": ("ренессанс страхование",),
    "AQUA": ("инарктика",),
    "LENT": ("лента",),
    "GCHE": ("черкизово",),
    "IRAO": ("интер рао",),
    "RTKMP": ("ростелеком привилегирован", "ростелеком-п", "ростелеком преф"),
}


def _action(text: str) -> str | None:
    low = text.lower()
    for action in ("SELL", "REDUCE", "ADD", "BUY"):
        if any(re.search(p, low) for p in ACTION_PATTERNS[action]):
            return action
    return None


def _asset(text: str) -> str | None:
    low = text.lower()
    # Resolve by the longest alias that actually matches this text. This avoids
    # reducing "Озон Фармацевтика" to the generic OZON alias "озон".
    matches: list[tuple[int, str]] = []
    for key, aliases in ASSET_ALIASES.items():
        for alias in aliases:
            if alias in low:
                matches.append((len(alias), key))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def parse_transcript(segments: Iterable[TranscriptSegment], source_url: str) -> list[PortfolioChange]:
    out: list[PortfolioChange] = []
    for seg in segments:
        action = _action(seg.text)
        if not action:
            continue
        asset = _asset(seg.text)
        # Quantity/price/amount extraction intentionally deferred until a value
        # can be tied unambiguously to the same security in context.
        confidence = 0.96 if asset else 0.70
        out.append(PortfolioChange(
            action=action,
            asset=asset,
            quantity=None,
            price=None,
            amount=None,
            evidence_text=seg.text.strip(),
            start_s=seg.start_s,
            end_s=seg.end_s,
            confidence=confidence,
            source_url=source_url,
        ))
    return out


def serialize(changes: Iterable[PortfolioChange]) -> list[dict]:
    return [asdict(x) for x in changes]
