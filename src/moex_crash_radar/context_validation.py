from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .calibration import signal_event_indices
from .history import DailyEvidence
from .moex import ISS_BASE, Candle, _get_json, parse_candles
from .oil_rub import brent_return_stress, rub_return_stress
from .rate_ofz import KeyRatePoint, key_rate_stress, parse_cbr_key_rate_html, rgbi_return_stress


@dataclass(frozen=True)
class HistoricalContextPoint:
    day: str
    score: float | None
    coverage: float
    rate_ofz_score: float | None
    oil_rub_score: float | None


@dataclass(frozen=True)
class ContextGateCandidate:
    threshold: float
    total_events: int
    false_events: int
    false_event_rate: float | None
    detected_episodes: int
    total_episodes: int
    median_lead_days: float | None
    context_coverage_rate: float


def _pct_return(values: list[float], lookback: int) -> float | None:
    if len(values) <= lookback or values[-1 - lookback] == 0:
        return None
    return (values[-1] / values[-1 - lookback] - 1.0) * 100.0


def _day(candle: Candle) -> str:
    return candle.begin[:10]


def _series_map(candles: list[Candle]) -> dict[str, float]:
    return {_day(c): c.close for c in candles}


def _point_in_time_return(series: dict[str, float], day: str, lookback: int) -> float | None:
    days = [d for d in series if d <= day]
    days.sort()
    if len(days) <= lookback:
        return None
    now = series[days[-1]]
    before = series[days[-1 - lookback]]
    if before == 0:
        return None
    return (now / before - 1.0) * 100.0


def _latest_key_rate(points: list[KeyRatePoint], day: str) -> KeyRatePoint | None:
    target = date.fromisoformat(day)
    eligible = [p for p in points if p.day <= target]
    return max(eligible, key=lambda p: p.day) if eligible else None


def historical_context_points(
    evidence: list[DailyEvidence],
    *,
    key_rates: list[KeyRatePoint],
    rgbi: list[Candle],
    brent: list[Candle],
    cnyrub: list[Candle],
) -> list[HistoricalContextPoint]:
    """Build point-in-time historical Context proxy without look-ahead.

    Historical OFZ cross-sectional median yield is not available from the live
    market endpoint, so Rate/OFZ uses key rate + RGBI returns and re-normalizes
    their live component weights. Oil/RUB preserves both Brent and CNYRUB 5/20D
    components. This is validation evidence, not full live-feature parity.
    """
    rgbi_map = _series_map(rgbi)
    brent_map = _series_map(brent)
    rub_map = _series_map(cnyrub)
    out: list[HistoricalContextPoint] = []

    for row in evidence:
        day = row.day
        rate_components: list[tuple[float, float]] = []
        kr = _latest_key_rate(key_rates, day)
        if kr is not None:
            rate_components.append((0.35, key_rate_stress(kr.rate)))
        r20 = _point_in_time_return(rgbi_map, day, 20)
        r5 = _point_in_time_return(rgbi_map, day, 5)
        if r20 is not None:
            rate_components.append((0.20, rgbi_return_stress(r20)))
        if r5 is not None:
            rate_components.append((0.10, rgbi_return_stress(r5)))
        rate_weight = sum(w for w, _ in rate_components)
        rate_score = (
            sum(w * s for w, s in rate_components) / rate_weight
            if rate_weight >= 0.45 else None
        )

        oil_components: list[tuple[float, float]] = []
        b20 = _point_in_time_return(brent_map, day, 20)
        b5 = _point_in_time_return(brent_map, day, 5)
        u20 = _point_in_time_return(rub_map, day, 20)
        u5 = _point_in_time_return(rub_map, day, 5)
        if b20 is not None:
            oil_components.append((0.30, brent_return_stress(b20)))
        if b5 is not None:
            oil_components.append((0.20, brent_return_stress(b5)))
        if u20 is not None:
            oil_components.append((0.30, rub_return_stress(u20)))
        if u5 is not None:
            oil_components.append((0.20, rub_return_stress(u5)))
        oil_weight = sum(w for w, _ in oil_components)
        has_brent = b20 is not None or b5 is not None
        has_rub = u20 is not None or u5 is not None
        oil_score = (
            sum(w * s for w, s in oil_components) / oil_weight
            if has_brent and has_rub and oil_weight >= 0.75 else None
        )

        available: list[tuple[float, float]] = []
        if rate_score is not None:
            available.append((0.35, rate_score))
        if oil_score is not None:
            available.append((0.25, oil_score))
        coverage = sum(w for w, _ in available)
        score = None
        if len(available) == 2 and coverage >= 0.50:
            score = round(sum(w * s for w, s in available) / coverage, 2)
        out.append(
            HistoricalContextPoint(
                day=day,
                score=score,
                coverage=round(coverage, 4),
                rate_ofz_score=round(rate_score, 2) if rate_score is not None else None,
                oil_rub_score=round(oil_score, 2) if oil_score is not None else None,
            )
        )
    return out


def validate_context_gate(
    evidence: list[DailyEvidence],
    context: list[HistoricalContextPoint],
    *,
    preferred: dict,
    episodes: tuple[tuple[str, str, str], ...],
    thresholds: tuple[float, ...] = (35.0, 45.0, 55.0, 65.0, 75.0),
) -> list[ContextGateCandidate]:
    event_indices = signal_event_indices(
        evidence,
        score_threshold=preferred["score_threshold"],
        confirmations=preferred["confirmations"],
        persistence=preferred["persistence"],
        max_5d_return_pct=preferred["max_5d_return_pct"],
        cooldown_rows=preferred["cooldown_rows"],
        require_breadth_volume=preferred["require_breadth_volume"],
        rearm_clear_rows=preferred["rearm_clear_rows"],
    )
    by_day = {x.day: x for x in context}
    candidates: list[ContextGateCandidate] = []

    for threshold in thresholds:
        kept: list[int] = []
        covered = 0
        false_events = 0
        for i in event_indices:
            cp = by_day.get(evidence[i].day)
            if cp is not None and cp.score is not None:
                covered += 1
                if cp.score >= threshold:
                    kept.append(i)
                    future = evidence[i : i + 21]
                    if len(future) >= 21:
                        dd = (min(x.close for x in future) / evidence[i].close - 1.0) * 100.0
                        if dd > -8.0:
                            false_events += 1

        leads: list[int] = []
        detected = 0
        for _, start, end in episodes:
            in_episode = [i for i in kept if start <= evidence[i].day <= end]
            if not in_episode:
                continue
            detected += 1
            i = in_episode[0]
            window = [x for x in evidence if evidence[i].day <= x.day <= end]
            if window:
                trough = min(window, key=lambda x: x.close)
                leads.append((date.fromisoformat(trough.day) - date.fromisoformat(evidence[i].day)).days)

        total = len(kept)
        candidates.append(
            ContextGateCandidate(
                threshold=threshold,
                total_events=total,
                false_events=false_events,
                false_event_rate=round(false_events / total, 4) if total else None,
                detected_episodes=detected,
                total_episodes=len(episodes),
                median_lead_days=round(float(median(leads)), 1) if leads else None,
                context_coverage_rate=round(covered / len(event_indices), 4) if event_indices else 0.0,
            )
        )
    return candidates


def _fetch_generic_history(url_base: str, *, start: str, end: str, max_pages: int = 30) -> list[Candle]:
    cursor = date.fromisoformat(start)
    end_day = date.fromisoformat(end)
    by_day: dict[str, Candle] = {}
    for _ in range(max_pages):
        params = {"from": cursor.isoformat(), "till": end, "interval": 24, "iss.meta": "off"}
        payload = _get_json(f"{url_base}?{urlencode(params)}")
        batch = parse_candles(payload)
        if not batch:
            break
        before = len(by_day)
        for candle in batch:
            by_day[_day(candle)] = candle
        last = date.fromisoformat(_day(batch[-1]))
        if last >= end_day or len(by_day) == before:
            break
        cursor = last + timedelta(days=1)
    return sorted(by_day.values(), key=lambda c: c.begin)


def fetch_rgbi_history(*, start: str, end: str) -> list[Candle]:
    return _fetch_generic_history(
        f"{ISS_BASE}/engines/stock/markets/index/securities/RGBI/candles.json",
        start=start,
        end=end,
    )


def fetch_cnyrub_history(*, start: str, end: str) -> list[Candle]:
    return _fetch_generic_history(
        f"{ISS_BASE}/engines/currency/markets/selt/boards/CETS/securities/CNYRUB_TOM/candles.json",
        start=start,
        end=end,
    )


def fetch_brent_history(*, start: str, end: str) -> list[Candle]:
    """Stitch one liquid September Brent future per year into a long proxy series.

    MOEX September Brent contracts typically trade for roughly a year, so the
    sequence BR-9.YY provides broad overlap with only one contract fetch/year.
    Overlap is resolved in favour of the contract with the later expiry year.
    """
    first_year = date.fromisoformat(start).year
    last_year = date.fromisoformat(end).year + 1
    by_day: dict[str, Candle] = {}
    for year in range(first_year, last_year + 1):
        secid = f"BR-9.{str(year)[-2:]}"
        url = f"{ISS_BASE}/engines/futures/markets/forts/boards/RFUD/securities/{secid}/candles.json"
        try:
            candles = _fetch_generic_history(url, start=start, end=end, max_pages=12)
        except Exception:
            continue
        for candle in candles:
            by_day[_day(candle)] = candle
    return sorted(by_day.values(), key=lambda c: c.begin)


def fetch_key_rate_history(*, start: str, end: str, timeout: int = 30) -> list[KeyRatePoint]:
    params = {
        "UniDbQuery.Posted": "True",
        "UniDbQuery.From": datetime.strptime(start, "%Y-%m-%d").strftime("%d.%m.%Y"),
        "UniDbQuery.To": datetime.strptime(end, "%Y-%m-%d").strftime("%d.%m.%Y"),
    }
    req = Request(
        f"https://www.cbr.ru/hd_base/KeyRate/?{urlencode(params)}",
        headers={"User-Agent": "moex-crash-radar/0.5.3"},
    )
    with urlopen(req, timeout=timeout) as response:  # nosec B310: fixed HTTPS CBR endpoint
        html = response.read().decode("utf-8", errors="replace")
    return parse_cbr_key_rate_html(html)
