from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from .breadth import breadth_signal, calculate_breadth
from .distribution import calculate_distribution, distribution_signal
from .engine import calculate_crash
from .features import derive_index_signals
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
    market_structure_score: float | None = None
    breadth_score: float | None = None
    volume_distribution_score: float | None = None
    volatility_liquidity_score: float | None = None


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


def _score(signals, key: str) -> float | None:
    signal = signals.get(key)
    return None if signal is None else round(signal.score, 2)


def build_daily_evidence(
    index_candles: Sequence[Candle],
    equity_candles: Mapping[str, Sequence[Candle]],
    *,
    min_equity_coverage: float = 0.70,
    warmup: int = 60,
) -> list[DailyEvidence]:
    """Build point-in-time evidence with no look-ahead.

    Only trailing data available as of the current index day is passed into
    breadth/distribution calculations. Critical component scores are persisted so
    later EXIT calibration can distinguish broad market deterioration from a high
    aggregate score caused by other components.
    """
    if not index_candles:
        return []

    result: list[DailyEvidence] = []
    basket_size = max(len(equity_candles), 1)
    equity_days = {ticker: [_day(c) for c in candles] for ticker, candles in equity_candles.items()}

    for i in range(warmup, len(index_candles)):
        index_history = index_candles[: i + 1]
        day = _day(index_history[-1])
        signals = derive_index_signals(index_history)

        point_histories: dict[str, Sequence[Candle]] = {}
        for ticker, full in equity_candles.items():
            days = equity_days[ticker]
            pos = bisect_right(days, day)
            if pos < 51:
                continue
            if days[pos - 1] != day:
                continue
            point_histories[ticker] = full[max(0, pos - 60) : pos]

        coverage = len(point_histories) / basket_size
        if coverage >= min_equity_coverage:
            breadth = calculate_breadth(point_histories)
            distribution = calculate_distribution(point_histories)
            if breadth is not None:
                signals["breadth"] = breadth_signal(breadth)
            if distribution is not None:
                signals["volume_distribution"] = distribution_signal(distribution)

        crash = calculate_crash(signals)
        result.append(
            DailyEvidence(
                day=day,
                close=index_history[-1].close,
                score=crash.score,
                state=crash.state.value,
                available_weight=round(crash.available_weight, 4),
                cash_signal=crash.cash_signal,
                critical_confirmations=crash.critical_confirmations,
                coverage=round(coverage, 4),
                market_structure_score=_score(signals, "market_structure"),
                breadth_score=_score(signals, "breadth"),
                volume_distribution_score=_score(signals, "volume_distribution"),
                volatility_liquidity_score=_score(signals, "volatility_liquidity"),
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
    """Count CASH days not followed by a material decline in the next horizon."""
    cash_days = 0
    false_days = 0
    for i, row in enumerate(evidence):
        if not row.cash_signal:
            continue
        future = evidence[i : i + horizon_days + 1]
        if len(future) < 2:
            continue
        cash_days += 1
        min_close = min(x.close for x in future)
        dd = (min_close / row.close - 1.0) * 100.0
        if dd > drawdown_threshold_pct:
            false_days += 1
    return cash_days, false_days
