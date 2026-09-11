from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .crowd import calculate_crowd
from .crowd_features import derive_crowd_inputs
from .moex import Candle


@dataclass(frozen=True)
class DailyCrowdEvidence:
    day: str
    close: float
    crowd_score: float | None
    crowd_state: str
    coverage: float
    available_groups: int
    velocity: float | None
    direction: str
    extreme: bool | None
    breadth_sentiment: float | None
    momentum_sentiment: float | None
    volume_sentiment: float | None
    volatility_sentiment: float | None


def _day(candle: Candle) -> str:
    return candle.begin[:10]


def _active_universe(
    day: str,
    equity_candles: Mapping[str, Sequence[Candle]],
    universe_by_effective_date: Mapping[str, Sequence[str]] | None,
) -> tuple[str, ...]:
    if not universe_by_effective_date:
        return tuple(equity_candles)
    effective_dates = sorted(universe_by_effective_date)
    pos = bisect_right(effective_dates, day)
    if pos == 0:
        return ()
    return tuple(universe_by_effective_date[effective_dates[pos - 1]])


def build_daily_crowd_evidence(
    index_candles: Sequence[Candle],
    equity_candles: Mapping[str, Sequence[Candle]],
    *,
    min_equity_coverage: float = 0.50,
    warmup: int = 60,
    universe_by_effective_date: Mapping[str, Sequence[str]] | None = None,
) -> list[DailyCrowdEvidence]:
    """Build R0.8 Crowd evidence using only data known at each historical day."""
    if not index_candles:
        return []

    result: list[DailyCrowdEvidence] = []
    equity_days = {ticker: [_day(c) for c in candles] for ticker, candles in equity_candles.items()}
    prior_score: float | None = None

    for i in range(warmup, len(index_candles)):
        index_history = index_candles[: i + 1]
        day = _day(index_history[-1])
        active = _active_universe(day, equity_candles, universe_by_effective_date)
        basket_size = len(active)
        point_histories: dict[str, Sequence[Candle]] = {}

        for ticker in active:
            full = equity_candles.get(ticker)
            days = equity_days.get(ticker)
            if not full or not days:
                continue
            pos = bisect_right(days, day)
            if pos < 21 or days[pos - 1] != day:
                continue
            point_histories[ticker] = full[max(0, pos - 60) : pos]

        market_coverage = (len(point_histories) / basket_size) if basket_size else 0.0
        if not basket_size or market_coverage < min_equity_coverage:
            point_histories = {}

        inputs = derive_crowd_inputs(index_history, point_histories)
        crowd = calculate_crowd(inputs, prior_score=prior_score)
        if crowd.score is not None:
            prior_score = crowd.score

        result.append(
            DailyCrowdEvidence(
                day=day,
                close=index_history[-1].close,
                crowd_score=crowd.score,
                crowd_state=crowd.state.value,
                coverage=crowd.coverage,
                available_groups=crowd.available_groups,
                velocity=crowd.velocity,
                direction=crowd.direction,
                extreme=crowd.extreme,
                breadth_sentiment=inputs.breadth_sentiment,
                momentum_sentiment=inputs.momentum_sentiment,
                volume_sentiment=inputs.volume_sentiment,
                volatility_sentiment=inputs.volatility_sentiment,
            )
        )
    return result


def transition_counts(rows: Sequence[DailyCrowdEvidence]) -> dict[str, int]:
    out: dict[str, int] = {}
    previous: str | None = None
    for row in rows:
        current = row.crowd_state
        if current == "DATA_INSUFFICIENT":
            continue
        if previous is not None and current != previous:
            key = f"{previous}->{current}"
            out[key] = out.get(key, 0) + 1
        previous = current
    return out


def serialize_rows(rows: Sequence[DailyCrowdEvidence]) -> list[dict]:
    return [asdict(row) for row in rows]
