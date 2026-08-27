from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BacktestPoint:
    date: str
    price: float
    crash_score: float
    bottom_score: float = 0.0


@dataclass(frozen=True)
class BacktestMetrics:
    signal_date: str | None
    crash_start_date: str | None
    trough_date: str | None
    lead_time_points: int | None
    drawdown_pct: float | None
    drawdown_after_signal_pct: float | None
    max_drawdown_avoided_pct: float | None
    recovery_lag_points: int | None
    buyback_date: str | None
    buyback_delay_points: int | None


def _max_drawdown(prices: Sequence[float]) -> float:
    peak = prices[0]
    worst = 0.0
    for price in prices:
        peak = max(peak, price)
        dd = price / peak - 1.0
        worst = min(worst, dd)
    return round(worst * 100.0, 2)


def evaluate_episode(
    points: Sequence[BacktestPoint],
    *,
    crash_threshold: float = 56.0,
    buyback_threshold: float = 71.0,
    crash_start_drawdown_pct: float = -5.0,
) -> BacktestMetrics:
    if len(points) < 2:
        raise ValueError("episode requires at least two points")

    prices = [p.price for p in points]
    peak = prices[0]
    crash_start_idx: int | None = None
    for i, price in enumerate(prices):
        peak = max(peak, price)
        dd = (price / peak - 1.0) * 100.0
        if crash_start_idx is None and dd <= crash_start_drawdown_pct:
            crash_start_idx = i

    signal_idx = next((i for i, p in enumerate(points) if p.crash_score >= crash_threshold), None)
    trough_idx = min(range(len(points)), key=lambda i: points[i].price)
    buyback_idx = next(
        (i for i in range(trough_idx, len(points)) if points[i].bottom_score >= buyback_threshold),
        None,
    )

    overall_dd = _max_drawdown(prices)
    after_signal_dd = None
    avoided = None
    if signal_idx is not None:
        signal_price = points[signal_idx].price
        trough_price = min(p.price for p in points[signal_idx:])
        after_signal_dd = round((trough_price / signal_price - 1.0) * 100.0, 2)
        avoided = round(abs(after_signal_dd), 2)

    recovery_lag = None
    if trough_idx is not None:
        pre_crash_peak = max(prices[: trough_idx + 1])
        recovery_idx = next(
            (i for i in range(trough_idx + 1, len(points)) if points[i].price >= pre_crash_peak),
            None,
        )
        if recovery_idx is not None:
            recovery_lag = recovery_idx - trough_idx

    lead = None
    if signal_idx is not None and crash_start_idx is not None:
        lead = crash_start_idx - signal_idx

    buyback_delay = None
    if buyback_idx is not None:
        buyback_delay = buyback_idx - trough_idx

    return BacktestMetrics(
        signal_date=points[signal_idx].date if signal_idx is not None else None,
        crash_start_date=points[crash_start_idx].date if crash_start_idx is not None else None,
        trough_date=points[trough_idx].date,
        lead_time_points=lead,
        drawdown_pct=overall_dd,
        drawdown_after_signal_pct=after_signal_dd,
        max_drawdown_avoided_pct=avoided,
        recovery_lag_points=recovery_lag,
        buyback_date=points[buyback_idx].date if buyback_idx is not None else None,
        buyback_delay_points=buyback_delay,
    )
