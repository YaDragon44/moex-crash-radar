from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from .engine import DataQuality, Signal
from .moex import ISS_BASE, _get_json, _table, parse_candles


@dataclass(frozen=True)
class MarketSeries:
    name: str
    secid: str
    closes: tuple[float, ...]
    last_day: date | None


@dataclass(frozen=True)
class OilRubResult:
    signal: Signal | None
    brent_secid: str | None
    brent_return_5d: float | None
    brent_return_20d: float | None
    cnyrub_return_5d: float | None
    cnyrub_return_20d: float | None
    component_coverage: float
    latest_day: str | None
    note: str


def _pct_return(closes: tuple[float, ...], lookback: int) -> float | None:
    if len(closes) <= lookback or closes[-1 - lookback] == 0:
        return None
    return round((closes[-1] / closes[-1 - lookback] - 1.0) * 100.0, 2)


def _interp(x: float, points: tuple[tuple[float, float], ...]) -> float:
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def brent_return_stress(return_pct: float) -> float:
    # Falling Brent is a negative external impulse for the Russian equity market.
    return round(_interp(return_pct, ((-25, 100), (-15, 90), (-8, 72), (-4, 55), (0, 30), (8, 12), (20, 0))), 2)


def rub_return_stress(cnyrub_return_pct: float) -> float:
    # CNYRUB rising means RUB weakening. Sharp depreciation is treated as stress.
    return round(_interp(cnyrub_return_pct, ((-20, 0), (-8, 10), (0, 30), (4, 52), (8, 70), (15, 90), (25, 100))), 2)


def select_nearest_brent_future(payload: dict, *, as_of: date | None = None) -> str | None:
    as_of = as_of or date.today()
    candidates: list[tuple[date, str]] = []
    for row in _table(payload, "securities"):
        secid = str(row.get("SECID") or "")
        if not secid.startswith("BR-"):
            continue
        raw = row.get("LASTTRADEDATE") or row.get("LASTDELDATE")
        if not raw:
            continue
        try:
            expiry = date.fromisoformat(str(raw)[:10])
        except ValueError:
            continue
        if expiry >= as_of:
            candidates.append((expiry, secid))
    return min(candidates)[1] if candidates else None


def fetch_nearest_brent_secid(*, as_of: date | None = None) -> str:
    params = {
        "iss.meta": "off",
        "iss.only": "securities",
        "securities.columns": "SECID,LASTTRADEDATE,LASTDELDATE",
    }
    url = f"{ISS_BASE}/engines/futures/markets/forts/boards/RFUD/securities.json?{urlencode(params)}"
    secid = select_nearest_brent_future(_get_json(url), as_of=as_of)
    if secid is None:
        raise ValueError("MOEX returned no active Brent future")
    return secid


def _fetch_series(url: str, *, name: str, secid: str) -> MarketSeries:
    candles = parse_candles(_get_json(url))
    closes = tuple(x.close for x in candles)
    last_day = None
    if candles:
        try:
            last_day = datetime.fromisoformat(candles[-1].begin.replace(" ", "T")).date()
        except ValueError:
            last_day = None
    return MarketSeries(name, secid, closes, last_day)


def fetch_brent_series(secid: str, *, as_of: date | None = None, lookback_days: int = 90) -> MarketSeries:
    as_of = as_of or date.today()
    start = as_of - timedelta(days=lookback_days)
    params = {"from": start.isoformat(), "till": as_of.isoformat(), "interval": 24, "iss.meta": "off"}
    url = f"{ISS_BASE}/engines/futures/markets/forts/boards/RFUD/securities/{secid}/candles.json?{urlencode(params)}"
    return _fetch_series(url, name="Brent", secid=secid)


def fetch_cnyrub_series(*, as_of: date | None = None, lookback_days: int = 90) -> MarketSeries:
    as_of = as_of or date.today()
    start = as_of - timedelta(days=lookback_days)
    params = {"from": start.isoformat(), "till": as_of.isoformat(), "interval": 24, "iss.meta": "off"}
    url = f"{ISS_BASE}/engines/currency/markets/selt/boards/CETS/securities/CNYRUB_TOM/candles.json?{urlencode(params)}"
    return _fetch_series(url, name="CNYRUB", secid="CNYRUB_TOM")


def calculate_oil_rub_signal(*, brent: MarketSeries | None, cnyrub: MarketSeries | None, today: date | None = None) -> OilRubResult:
    today = today or date.today()
    b5 = _pct_return(brent.closes, 5) if brent else None
    b20 = _pct_return(brent.closes, 20) if brent else None
    r5 = _pct_return(cnyrub.closes, 5) if cnyrub else None
    r20 = _pct_return(cnyrub.closes, 20) if cnyrub else None

    components: list[tuple[float, float]] = []
    if b20 is not None:
        components.append((0.30, brent_return_stress(b20)))
    if b5 is not None:
        components.append((0.20, brent_return_stress(b5)))
    if r20 is not None:
        components.append((0.30, rub_return_stress(r20)))
    if r5 is not None:
        components.append((0.20, rub_return_stress(r5)))
    coverage = round(sum(w for w, _ in components), 4)

    last_days = [x.last_day for x in (brent, cnyrub) if x is not None and x.last_day is not None]
    latest = min(last_days) if len(last_days) == 2 else None
    fresh = latest is not None and (today - latest).days <= 5
    has_oil = b5 is not None or b20 is not None
    has_rub = r5 is not None or r20 is not None
    if not fresh or not has_oil or not has_rub or coverage < 0.75:
        return OilRubResult(
            signal=None,
            brent_secid=brent.secid if brent else None,
            brent_return_5d=b5,
            brent_return_20d=b20,
            cnyrub_return_5d=r5,
            cnyrub_return_20d=r20,
            component_coverage=coverage,
            latest_day=latest.isoformat() if latest else None,
            note="DATA_INSUFFICIENT: both Brent and CNYRUB, freshness <=5d and >=75% component coverage are required.",
        )

    score = round(sum(w * s for w, s in components) / coverage, 2)
    quality = DataQuality.LIVE if latest is not None and (today - latest).days <= 3 else DataQuality.DELAYED
    return OilRubResult(
        signal=Signal(score, quality),
        brent_secid=brent.secid if brent else None,
        brent_return_5d=b5,
        brent_return_20d=b20,
        cnyrub_return_5d=r5,
        cnyrub_return_20d=r20,
        component_coverage=coverage,
        latest_day=latest.isoformat() if latest else None,
        note="Relative Oil/RUB external stress composite; not a probability and not Crowd Score.",
    )


def collect_oil_rub(*, as_of: date | None = None) -> OilRubResult:
    as_of = as_of or date.today()
    brent: MarketSeries | None = None
    cnyrub: MarketSeries | None = None
    try:
        secid = fetch_nearest_brent_secid(as_of=as_of)
        brent = fetch_brent_series(secid, as_of=as_of)
    except Exception:
        brent = None
    try:
        cnyrub = fetch_cnyrub_series(as_of=as_of)
    except Exception:
        cnyrub = None
    return calculate_oil_rub_signal(brent=brent, cnyrub=cnyrub, today=as_of)
