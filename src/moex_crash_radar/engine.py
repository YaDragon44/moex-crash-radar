from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence


class DataQuality(str, Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    STALE = "STALE"
    ERROR = "ERROR"
    NA = "N/A"


class CrashState(str, Enum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    DEFENSIVE = "DEFENSIVE"
    HIGH_RISK = "HIGH_RISK"
    CRASH = "CRASH"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


class BottomState(str, Enum):
    NO_BOTTOM = "NO_BOTTOM"
    CAPITULATION_WATCH = "CAPITULATION_WATCH"
    BOTTOM_FORMING = "BOTTOM_FORMING"
    ACCUMULATION = "ACCUMULATION"
    BUY_BACK_READY = "BUY_BACK_READY"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


CRASH_WEIGHTS: Mapping[str, float] = {
    "market_structure": 0.18,
    "breadth": 0.17,
    "volume_distribution": 0.14,
    "volatility_liquidity": 0.13,
    "levels_momentum": 0.10,
    "rate_ofz": 0.09,
    "oil_rub": 0.07,
    "macro_earnings": 0.06,
    "news_geopolitics": 0.06,
}

BOTTOM_WEIGHTS: Mapping[str, float] = {
    "selling_climax": 0.20,
    "volume_absorption": 0.15,
    "breadth_divergence": 0.15,
    "momentum_divergence": 0.10,
    "liquidity_sweep_reclaim": 0.15,
    "choch_bos_up": 0.15,
    "news_non_response": 0.10,
}

CRITICAL_CRASH_GROUPS = {
    "market_structure",
    "breadth",
    "volume_distribution",
    "volatility_liquidity",
}


@dataclass(frozen=True)
class Signal:
    score: float
    quality: DataQuality = DataQuality.LIVE

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("score must be in [0, 100]")


@dataclass(frozen=True)
class CrashResult:
    score: float | None
    state: CrashState
    quality: DataQuality
    available_weight: float
    critical_confirmations: int
    cash_signal: bool


@dataclass(frozen=True)
class BottomResult:
    score: float | None
    state: BottomState
    quality: DataQuality
    available_weight: float
    buy_back_signal: bool


def _usable(signal: Signal) -> bool:
    return signal.quality in {DataQuality.LIVE, DataQuality.DELAYED}


def _aggregate(signals: Mapping[str, Signal], weights: Mapping[str, float]) -> tuple[float | None, float, DataQuality]:
    weighted = 0.0
    available_weight = 0.0
    qualities: list[DataQuality] = []

    for key, weight in weights.items():
        signal = signals.get(key)
        if signal is None or not _usable(signal):
            continue
        weighted += signal.score * weight
        available_weight += weight
        qualities.append(signal.quality)

    if available_weight < 0.70:
        return None, available_weight, DataQuality.ERROR

    normalized = weighted / available_weight
    overall_quality = DataQuality.DELAYED if DataQuality.DELAYED in qualities else DataQuality.LIVE
    return round(normalized, 2), available_weight, overall_quality


def crash_state(score: float) -> CrashState:
    if score <= 25:
        return CrashState.NORMAL
    if score <= 40:
        return CrashState.CAUTION
    if score <= 55:
        return CrashState.DEFENSIVE
    if score <= 70:
        return CrashState.HIGH_RISK
    return CrashState.CRASH


def bottom_state(score: float) -> BottomState:
    if score <= 30:
        return BottomState.NO_BOTTOM
    if score <= 50:
        return BottomState.CAPITULATION_WATCH
    if score <= 70:
        return BottomState.BOTTOM_FORMING
    if score <= 85:
        return BottomState.ACCUMULATION
    return BottomState.BUY_BACK_READY


def calculate_crash(signals: Mapping[str, Signal]) -> CrashResult:
    score, available_weight, quality = _aggregate(signals, CRASH_WEIGHTS)
    if score is None:
        return CrashResult(None, CrashState.DATA_INSUFFICIENT, DataQuality.ERROR, available_weight, 0, False)

    confirmations = sum(
        1
        for key in CRITICAL_CRASH_GROUPS
        if key in signals and _usable(signals[key]) and signals[key].score >= 60
    )
    state = crash_state(score)
    cash_signal = score >= 56 and confirmations >= 3
    return CrashResult(score, state, quality, available_weight, confirmations, cash_signal)


def calculate_bottom(signals: Mapping[str, Signal]) -> BottomResult:
    score, available_weight, quality = _aggregate(signals, BOTTOM_WEIGHTS)
    if score is None:
        return BottomResult(None, BottomState.DATA_INSUFFICIENT, DataQuality.ERROR, available_weight, False)

    state = bottom_state(score)
    required = ("liquidity_sweep_reclaim", "choch_bos_up", "breadth_divergence")
    confirmations = sum(
        1
        for key in required
        if key in signals and _usable(signals[key]) and signals[key].score >= 60
    )
    buy_back = score >= 71 and confirmations >= 2
    return BottomResult(score, state, quality, available_weight, buy_back)


def crash_momentum(history: Sequence[float], lookback: int = 5) -> float | None:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if len(history) <= lookback:
        return None
    return round(history[-1] - history[-1 - lookback], 2)


def downside_velocity(prices: Sequence[float], lookback: int = 5) -> float | None:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if len(prices) <= lookback:
        return None
    start = prices[-1 - lookback]
    if start == 0:
        return None
    return round((prices[-1] / start - 1.0) * 100.0, 2)


def breadth_divergence(index_returns: Sequence[float], breadth_returns: Sequence[float], window: int = 5) -> bool:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(index_returns) < window or len(breadth_returns) < window:
        return False
    idx = sum(index_returns[-window:])
    brd = sum(breadth_returns[-window:])
    return idx >= -1.0 and brd <= -5.0
