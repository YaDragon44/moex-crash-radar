from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from .engine import CrashResult, calculate_crash
from .features import derive_index_signals
from .breadth import breadth_signal
from .distribution import distribution_signal
from .moex import Candle


@dataclass(frozen=True)
class DailyEvidence:
    day: str
    close: float
    score: float | None
    state: str
    available_weight: float
    cash_signal: bool
    critical_confirmations: int
    coverage: float


@dataclass(frozen=True)
class EpisodeResult:
    name: str
    start: str
    trough: str
    start_close: float
    trough_close: float
    drawdown_pct: float
    first_high_risk: str | None
    first_cash: str | None
    lead_days_high_risk: int | None
    lead_days_cash: int | None
    false_positive: bool


def _day(c: Candle) -> str:
    return c.begin[:10]


def _days_between(a: str | None, b: str) -> int | None:
    if a is None:
        return None
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days


def build_daily_evidence(
    index_candles: Sequence[Candle],
    equity_candles: Mapping[str, Sequence[Candle]],
    *,
    min_equity_coverage: float = 0.70,
    warmup: int = 60,
) -> list[DailyEvidence]:
    """Build point-in-time evidence using only data available on each day.

    No future candles are passed into feature functions. Equity coverage is measured
    against the configured basket; insufficient coverage suppresses breadth and
    distribution rather than imputing values.
    """
    if not index_candles:
        return []

    equity_by_day: dict[str, dict[str, Candle]] = {}
    for ticker, candles in equity_candles.items():
        equity_by_day[ticker] = {_day(c): c for c in candles}

    result: list[DailyEvidence] = []
    basket_size = max(len(equity_by_day), 1)

    for i in range(warmup, len(index_candles)):
        history = index_candles[: i + 1]
        day = _day(history[-1])
        signals = derive_index_signals(history)

        point_histories: dict[str, list[Candle]] = {}
        available = 0
        for ticker, full in equity_candles.items():
            hist = [c for c in full if _day(c) <= day]
            if len(hist) >= 50 and _day(hist[-1]) == day:
                point_histories[ticker] = hist
                available += 1

        coverage = available / basket_size
        if coverage >= min_equity_coverage:
            b = breadth_signal(point_histories)
            d = distribution_signal(point_histories)
            if b is not None:
                signals["breadth"] = b
            if d is not None:
                signals["volume_distribution"] = d

        crash = calculate_crash(signals)
        result.append(
            DailyEvidence(
                day=day,
                close=history[-1].close,
                score=crash.score,
                state=crash.state.value,
                available_weight=round(crash.available_weight, 4),
                cash_signal=crash.cash_signal,
                critical_confirmations=crash.critical_confirmations,
                coverage=round(coverage, 4),
            )
        )
    return result


def evaluate_episode(
    evidence: Sequence[DailyEvidence],
    *,
    name: str,
    start: str,
    end: str,
    material_drawdown_pct: float = -10.0,
) -> EpisodeResult:
    rows = [r for r in evidence if start <= r.day <= end]
    if not rows:
        raise ValueError(f"no evidence rows for {name}")

    start_row = rows[0]
    trough = min(rows, key=lambda r: r.close)
    drawdown = (trough.close / start_row.close - 1.0) * 100.0

    pre_trough = [r for r in rows if r.day <= trough.day]
    high = next((r.day for r in pre_trough if r.score is not None and r.score >= 56), None)
    cash = next((r.day for r in pre_trough if r.cash_signal), None)

    return EpisodeResult(
        name=name,
        start=start_row.day,
        trough=trough.day,
        start_close=start_row.close,
        trough_close=trough.close,
        drawdown_pct=round(drawdown, 2),
        first_high_risk=high,
        first_cash=cash,
        lead_days_high_risk=_days_between(high, trough.day),
        lead_days_cash=_days_between(cash, trough.day),
        false_positive=drawdown > material_drawdown_pct,
    )


def count_false_positive_days(
    evidence: Sequence[DailyEvidence], *, horizon_days: int = 20, drawdown_threshold_pct: float = -8.0
) -> tuple[int, int]:
    """Count CASH days not followed by a material decline in the next horizon.

    This is a simple calibration metric, not a trading-PnL backtest.
    """
    cash_days = 0
    false_days = 0
    for i, row in enumerate(evidence):
        if not row.cash_signal:
            continue
        cash_days += 1
        future = evidence[i : i + horizon_days + 1]
        if len(future) < 2:
            continue
        min_close = min(x.close for x in future)
        dd = (min_close / row.close - 1.0) * 100.0
        if dd > drawdown_threshold_pct:
            false_days += 1
    return cash_days, false_days
