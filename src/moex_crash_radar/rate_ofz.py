from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .engine import DataQuality, Signal
from .moex import ISS_BASE, _get_json, _table, fetch_index_candles


CBR_KEY_RATE_URL = "https://www.cbr.ru/hd_base/KeyRate/"


@dataclass(frozen=True)
class KeyRatePoint:
    day: date
    rate: float


@dataclass(frozen=True)
class OfzMarketPoint:
    secid: str
    maturity: date | None
    yield_pct: float
    value_today: float | None


@dataclass(frozen=True)
class RateOfzResult:
    signal: Signal | None
    key_rate: float | None
    key_rate_day: str | None
    median_long_ofz_yield: float | None
    ofz_count: int
    rgbi_return_5d: float | None
    rgbi_return_20d: float | None
    component_coverage: float
    note: str


def parse_cbr_key_rate_html(html: str) -> list[KeyRatePoint]:
    pairs = re.findall(
        r"<td[^>]*>\s*(\d{2}\.\d{2}\.\d{4})\s*</td>\s*<td[^>]*>\s*([0-9]+(?:[\.,][0-9]+)?)\s*</td>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    result: list[KeyRatePoint] = []
    for day_s, rate_s in pairs:
        try:
            result.append(
                KeyRatePoint(
                    day=datetime.strptime(day_s, "%d.%m.%Y").date(),
                    rate=float(rate_s.replace(",", ".")),
                )
            )
        except ValueError:
            continue
    return sorted(result, key=lambda x: x.day)


def fetch_key_rate(*, as_of: date | None = None, lookback_days: int = 45, timeout: int = 20) -> KeyRatePoint:
    as_of = as_of or date.today()
    start = as_of - timedelta(days=lookback_days)
    params = {
        "UniDbQuery.Posted": "True",
        "UniDbQuery.From": start.strftime("%d.%m.%Y"),
        "UniDbQuery.To": as_of.strftime("%d.%m.%Y"),
    }
    url = f"{CBR_KEY_RATE_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "moex-crash-radar/0.5.1"})
    with urlopen(req, timeout=timeout) as response:  # nosec B310: fixed HTTPS CBR endpoint
        html = response.read().decode("utf-8", errors="replace")
    points = parse_cbr_key_rate_html(html)
    if not points:
        raise ValueError("CBR key-rate page returned no parsable rows")
    return points[-1]


def parse_ofz_market(payload: dict, *, min_years: float = 4.0, as_of: date | None = None) -> list[OfzMarketPoint]:
    as_of = as_of or date.today()
    securities = {row.get("SECID"): row for row in _table(payload, "securities") if row.get("SECID")}
    result: list[OfzMarketPoint] = []
    for row in _table(payload, "marketdata"):
        secid = row.get("SECID")
        yld = row.get("YIELD")
        if not secid or yld is None or secid not in securities:
            continue
        sec = securities[secid]
        mat_raw = sec.get("MATDATE")
        maturity = None
        if mat_raw:
            try:
                maturity = date.fromisoformat(str(mat_raw)[:10])
            except ValueError:
                maturity = None
        if maturity is None or (maturity - as_of).days < int(min_years * 365.25):
            continue
        try:
            y = float(yld)
        except (TypeError, ValueError):
            continue
        if not 0 < y < 100:
            continue
        value = row.get("VALTODAY")
        result.append(
            OfzMarketPoint(
                secid=str(secid),
                maturity=maturity,
                yield_pct=y,
                value_today=float(value) if value is not None else None,
            )
        )
    return result


def fetch_long_ofz_market(*, as_of: date | None = None) -> list[OfzMarketPoint]:
    params = {
        "iss.meta": "off",
        "iss.only": "securities,marketdata",
        "securities.columns": "SECID,MATDATE",
        "marketdata.columns": "SECID,YIELD,VALTODAY",
    }
    url = f"{ISS_BASE}/engines/stock/markets/bonds/boards/TQOB/securities.json?{urlencode(params)}"
    return parse_ofz_market(_get_json(url), as_of=as_of)


def _interp(x: float, points: tuple[tuple[float, float], ...]) -> float:
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def key_rate_stress(rate: float) -> float:
    return round(_interp(rate, ((0, 0), (7, 10), (10, 30), (14, 50), (18, 75), (25, 100))), 2)


def ofz_yield_stress(yield_pct: float) -> float:
    return round(_interp(yield_pct, ((0, 0), (8, 10), (12, 35), (16, 65), (20, 90), (30, 100))), 2)


def rgbi_return_stress(return_pct: float) -> float:
    # Falling sovereign bond prices / rising yields are stress; strong positive returns are supportive.
    return round(_interp(return_pct, ((-10, 100), (-6, 85), (-3, 60), (0, 30), (3, 10), (8, 0))), 2)


def _pct_return(closes: list[float], lookback: int) -> float | None:
    if len(closes) <= lookback or closes[-1 - lookback] == 0:
        return None
    return round((closes[-1] / closes[-1 - lookback] - 1.0) * 100.0, 2)


def calculate_rate_ofz_signal(
    *,
    key_rate: KeyRatePoint | None,
    long_ofz: list[OfzMarketPoint],
    rgbi_closes: list[float],
    today: date | None = None,
) -> RateOfzResult:
    today = today or date.today()
    components: list[tuple[float, float]] = []
    key_ok = key_rate is not None and (today - key_rate.day).days <= 7
    if key_ok and key_rate is not None:
        components.append((0.35, key_rate_stress(key_rate.rate)))

    yields = [x.yield_pct for x in long_ofz]
    median_yield = round(median(yields), 2) if len(yields) >= 5 else None
    if median_yield is not None:
        components.append((0.35, ofz_yield_stress(median_yield)))

    r5 = _pct_return(rgbi_closes, 5)
    r20 = _pct_return(rgbi_closes, 20)
    if r20 is not None:
        components.append((0.20, rgbi_return_stress(r20)))
    if r5 is not None:
        components.append((0.10, rgbi_return_stress(r5)))

    coverage = round(sum(w for w, _ in components), 4)
    has_bond_component = median_yield is not None or r20 is not None or r5 is not None
    if not key_ok or not has_bond_component or coverage < 0.65:
        return RateOfzResult(
            signal=None,
            key_rate=key_rate.rate if key_rate else None,
            key_rate_day=key_rate.day.isoformat() if key_rate else None,
            median_long_ofz_yield=median_yield,
            ofz_count=len(yields),
            rgbi_return_5d=r5,
            rgbi_return_20d=r20,
            component_coverage=coverage,
            note="DATA_INSUFFICIENT: key rate plus >=1 bond-market component and >=65% component coverage are required.",
        )

    score = round(sum(w * s for w, s in components) / coverage, 2)
    quality = DataQuality.LIVE if key_rate and (today - key_rate.day).days <= 3 else DataQuality.DELAYED
    return RateOfzResult(
        signal=Signal(score, quality),
        key_rate=key_rate.rate if key_rate else None,
        key_rate_day=key_rate.day.isoformat() if key_rate else None,
        median_long_ofz_yield=median_yield,
        ofz_count=len(yields),
        rgbi_return_5d=r5,
        rgbi_return_20d=r20,
        component_coverage=coverage,
        note="Relative Rate/OFZ stress composite; not a probability and not Crowd Score.",
    )


def collect_rate_ofz(*, as_of: date | None = None) -> RateOfzResult:
    as_of = as_of or date.today()
    key_rate: KeyRatePoint | None = None
    long_ofz: list[OfzMarketPoint] = []
    rgbi_closes: list[float] = []

    try:
        key_rate = fetch_key_rate(as_of=as_of)
    except Exception:
        key_rate = None
    try:
        long_ofz = fetch_long_ofz_market(as_of=as_of)
    except Exception:
        long_ofz = []
    try:
        start = (as_of - timedelta(days=80)).isoformat()
        candles = fetch_index_candles("RGBI", start=start, end=as_of.isoformat())
        rgbi_closes = [x.close for x in candles]
    except Exception:
        rgbi_closes = []

    return calculate_rate_ofz_signal(
        key_rate=key_rate,
        long_ofz=long_ofz,
        rgbi_closes=rgbi_closes,
        today=as_of,
    )
