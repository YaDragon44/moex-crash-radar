from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Regime(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    RANGE = "RANGE"
    UNKNOWN = "UNKNOWN"


class Decision(str, Enum):
    TRADE_READY = "TRADE_READY"
    WAIT = "WAIT"
    NO_TRADE = "NO_TRADE"


class NoTradeReason(str, Enum):
    DATA_QUALITY = "DATA_QUALITY"
    RANGE = "RANGE"
    MID_RANGE = "MID_RANGE"
    OI_INSUFFICIENT = "OI_INSUFFICIENT"
    POSITIONING_CONTRADICTION = "POSITIONING_CONTRADICTION"
    RVOL_LOW = "RVOL_LOW"
    NO_TRIGGER = "NO_TRIGGER"
    STOP_TOO_WIDE = "STOP_TOO_WIDE"
    RR_INSUFFICIENT = "RR_INSUFFICIENT"
    LATE_ENTRY = "LATE_ENTRY"


@dataclass(frozen=True)
class OIFlowConfig:
    oi_percentile_min: float = 75.0
    rvol_min: float = 1.0
    breakout_rvol_min: float = 1.2
    stop_atr_max: float = 1.5
    min_rr: float = 2.0
    late_entry_atr_max: float = 0.5
    atr_stop_buffer: float = 0.2
    risk_per_trade: float = 0.005
    time_exit_bars: int = 4
    time_exit_min_r: float = 0.5


@dataclass(frozen=True)
class SignalSnapshot:
    data_ready: bool
    regime: Regime
    valid_location: bool
    oi_expanding: bool
    oi_percentile: float
    positioning_contradiction: bool
    rvol: float
    breakout_setup: bool
    trigger_confirmed: bool
    stop_distance_atr: float
    potential_rr: float
    entry_distance_atr: float


@dataclass(frozen=True)
class GateResult:
    decision: Decision
    direction: Direction | None
    reason: NoTradeReason | None


def direction_from_regime(regime: Regime) -> Direction | None:
    if regime is Regime.BULL:
        return Direction.LONG
    if regime is Regime.BEAR:
        return Direction.SHORT
    return None


def evaluate_signal(snapshot: SignalSnapshot, config: OIFlowConfig = OIFlowConfig()) -> GateResult:
    """Evaluate v1.0 gates in a deterministic, fail-closed order.

    The function intentionally does not infer missing values and does not score
    partial evidence. A failed mandatory gate yields NO_TRADE; lack of a trigger
    yields WAIT so the candidate may be re-evaluated on a later closed bar.
    """
    if not snapshot.data_ready:
        return GateResult(Decision.NO_TRADE, None, NoTradeReason.DATA_QUALITY)

    direction = direction_from_regime(snapshot.regime)
    if direction is None:
        return GateResult(Decision.NO_TRADE, None, NoTradeReason.RANGE)

    if not snapshot.valid_location:
        return GateResult(Decision.NO_TRADE, direction, NoTradeReason.MID_RANGE)

    if (not snapshot.oi_expanding) or snapshot.oi_percentile < config.oi_percentile_min:
        return GateResult(Decision.NO_TRADE, direction, NoTradeReason.OI_INSUFFICIENT)

    if snapshot.positioning_contradiction:
        return GateResult(Decision.NO_TRADE, direction, NoTradeReason.POSITIONING_CONTRADICTION)

    required_rvol = config.breakout_rvol_min if snapshot.breakout_setup else config.rvol_min
    if snapshot.rvol < required_rvol:
        return GateResult(Decision.NO_TRADE, direction, NoTradeReason.RVOL_LOW)

    if not snapshot.trigger_confirmed:
        return GateResult(Decision.WAIT, direction, NoTradeReason.NO_TRIGGER)

    if snapshot.stop_distance_atr > config.stop_atr_max:
        return GateResult(Decision.NO_TRADE, direction, NoTradeReason.STOP_TOO_WIDE)

    if snapshot.potential_rr < config.min_rr:
        return GateResult(Decision.NO_TRADE, direction, NoTradeReason.RR_INSUFFICIENT)

    if snapshot.entry_distance_atr > config.late_entry_atr_max:
        return GateResult(Decision.NO_TRADE, direction, NoTradeReason.LATE_ENTRY)

    return GateResult(Decision.TRADE_READY, direction, None)
