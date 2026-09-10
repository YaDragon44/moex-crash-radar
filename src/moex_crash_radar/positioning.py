from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from urllib.parse import urlencode

from .moex import ISS_BASE, _get_json, _table


@dataclass(frozen=True)
class PositioningRow:
    day: str
    ticker: str
    client_group: str
    net_position: int
    long_contracts: int
    short_contracts: int
    long_entities: int
    short_entities: int


@dataclass(frozen=True)
class PositioningSnapshot:
    ticker: str
    as_of: str | None
    quality: str
    individuals: PositioningRow | None
    legal_entities: PositioningRow | None
    total_open_interest: int | None
    retail_net: int | None
    legal_net: int | None
    directional_divergence: bool | None
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


def _ival(value) -> int:
    if value is None:
        return 0
    return int(float(value))


def parse_futoi(payload: dict) -> list[PositioningRow]:
    rows = _table(payload, "futoi")
    out: list[PositioningRow] = []
    for row in rows:
        ticker = row.get("ticker") or row.get("TICKER")
        group = row.get("clgroup") or row.get("CLGROUP")
        day = row.get("tradedate") or row.get("TRADEDATE") or row.get("date") or row.get("DATE")
        if not ticker or not group or not day:
            continue
        out.append(PositioningRow(
            day=str(day)[:10], ticker=str(ticker).upper(), client_group=str(group).upper(),
            net_position=_ival(row.get("pos") if "pos" in row else row.get("POS")),
            long_contracts=_ival(row.get("pos_long") if "pos_long" in row else row.get("POS_LONG")),
            short_contracts=abs(_ival(row.get("pos_short") if "pos_short" in row else row.get("POS_SHORT"))),
            long_entities=_ival(row.get("pos_long_num") if "pos_long_num" in row else row.get("POS_LONG_NUM")),
            short_entities=_ival(row.get("pos_short_num") if "pos_short_num" in row else row.get("POS_SHORT_NUM")),
        ))
    return out


def fetch_futoi(ticker: str, *, start: str | None = None, end: str | None = None) -> list[PositioningRow]:
    params = {"iss.meta": "off", "iss.only": "futoi"}
    if start:
        params["from"] = start
    if end:
        params["till"] = end
    url = f"{ISS_BASE}/analyticalproducts/futoi/securities/{ticker.lower()}.json?{urlencode(params)}"
    return parse_futoi(_get_json(url))


def build_positioning_snapshot(ticker: str, rows: list[PositioningRow], *, today: str | None = None) -> PositioningSnapshot:
    source = "MOEX ISS analyticalproducts/futoi"
    if not rows:
        return PositioningSnapshot(ticker.upper(), None, "N/A", None, None, None, None, None, None, source)
    latest_day = max(x.day for x in rows)
    latest = [x for x in rows if x.day == latest_day]
    fiz = next((x for x in latest if x.client_group == "FIZ"), None)
    yur = next((x for x in latest if x.client_group == "YUR"), None)
    if not fiz or not yur:
        return PositioningSnapshot(ticker.upper(), latest_day, "N/A", fiz, yur, None, fiz.net_position if fiz else None, yur.net_position if yur else None, None, source)
    ref = date.fromisoformat(today) if today else date.today()
    age = (ref - date.fromisoformat(latest_day)).days
    quality = "LIVE" if age <= 1 else ("DELAYED" if age <= 3 else "STALE")
    # Each open contract has a long and a short side, so divide gross sides by two.
    total_oi = (fiz.long_contracts + fiz.short_contracts + yur.long_contracts + yur.short_contracts) // 2
    divergence = (fiz.net_position > 0 > yur.net_position) or (yur.net_position > 0 > fiz.net_position)
    return PositioningSnapshot(ticker.upper(), latest_day, quality, fiz, yur, total_oi, fiz.net_position, yur.net_position, divergence, source)
