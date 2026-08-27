from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Mapping, Sequence

from .engine import Signal
from .moex import Candle


@dataclass(frozen=True)
class DistributionSnapshot:
    usable_size: int
    pct_down_rvol: float
    pct_distribution_5d: float
    mean_down_up_volume_ratio: float


def calculate_distribution(universe: Mapping[str, Sequence[Candle]]) -> DistributionSnapshot | None:
    latest_flags: list[bool] = []
    distribution_flags: list[bool] = []
    ratios: list[float] = []

    for candles in universe.values():
        if len(candles) < 25:
            continue
        recent = candles[-21:]
        volumes = [c.volume for c in recent]
        if any(v is None or v <= 0 for v in volumes):
            continue

        avg20 = mean(float(v) for v in volumes[:-1])
        last = recent[-1]
        last_rvol = float(last.volume) / avg20 if avg20 > 0 else 0.0
        latest_flags.append(last.close < last.open and last_rvol >= 1.3)

        down_vol = sum(float(c.volume) for c in recent[-5:] if c.close < c.open)
        up_vol = sum(float(c.volume) for c in recent[-5:] if c.close >= c.open)
        ratio = down_vol / max(up_vol, 1.0)
        ratios.append(ratio)
        distribution_flags.append(ratio >= 1.4)

    usable = len(latest_flags)
    if usable == 0:
        return None

    pct = lambda count: round(100.0 * count / usable, 2)
    return DistributionSnapshot(
        usable_size=usable,
        pct_down_rvol=pct(sum(latest_flags)),
        pct_distribution_5d=pct(sum(distribution_flags)),
        mean_down_up_volume_ratio=round(mean(ratios), 3),
    )


def distribution_signal(snapshot: DistributionSnapshot) -> Signal:
    score = 0.0
    if snapshot.pct_down_rvol >= 50:
        score += 40
    elif snapshot.pct_down_rvol >= 30:
        score += 25
    elif snapshot.pct_down_rvol >= 15:
        score += 12

    if snapshot.pct_distribution_5d >= 60:
        score += 40
    elif snapshot.pct_distribution_5d >= 40:
        score += 25
    elif snapshot.pct_distribution_5d >= 25:
        score += 12

    if snapshot.mean_down_up_volume_ratio >= 2.0:
        score += 20
    elif snapshot.mean_down_up_volume_ratio >= 1.4:
        score += 12

    return Signal(min(score, 100.0))
