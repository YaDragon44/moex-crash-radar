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
    oi_percentile_threshold: float = 75.0
    rvol_minimum: float = 1.0
    breakout_rvol_minimum: float = 1.2
    stop_buffer_atr: float = 0.2
    max_stop_atr: float = 1.5
    min_rr: float = 2.0
    max_late_entry_atr: float = 0.5


@dataclass(frozen=True)
class SignalState:
    quality_ready: bool
    regime: Regime
    valid_location: bool
    mid_range: bool
    oi_change: float
    oi_percentile: float
    legal_net_delta: float
    retail_net_delta: float
    rvol: float
    trigger_confirmed: bool
    breakout_setup: bool
    atr: float
    entry: float
    structural_stop: float
    nearest_target: float
    trigger_price: float


@dataclass(frozen=True)
class TradeDecision:
    decision: Decision
    direction: Direction | None
    reason: NoTradeReason | None
    stop: float | None
    risk_distance: float | None
    potential_rr: float | None


def _direction(regime: Regime) -> Direction | None:
    if regime is Regime.BULL:
        return Direction.LONG
    if regime is Regime.BEAR:
        return Direction.SHORT
    return None


def _positioning_contradicts(direction: Direction, legal_delta: float, retail_delta: float) -> bool:
    """Conservative v1 contradiction gate.

    LONG is rejected only when legal positioning deteriorates AND retail positioning
    becomes more long. SHORT is the mirror image. One group alone cannot veto a trade.
    This intentionally avoids the unsupported assumption that legal entities are
    always 'smart money'.
    """
    if direction is Direction.LONG:
        return legal_delta < 0 and retail_delta > 0
    return legal_delta > 0 and retail_delta < 0


def evaluate_signal(state: SignalState, config: OIFlowConfig = OIFlowConfig()) -> TradeDecision:
    """Evaluate one fully point-in-time 1H candidate.

    The caller must provide values computed only from bars/positioning snapshots
    available at the decision timestamp. Entry is expected to be the next 1H bar
    open; this function never derives future values.
    """
    if not state.quality_ready:
        return TradeDecision(Decision.NO_TRADE, None, NoTradeReason.DATA_QUALITY, None, None, None)

    direction = _direction(state.regime)
    if direction is None:
        return TradeDecision(Decision.NO_TRADE, None, NoTradeReason.RANGE, None, None, None)

    if not state.valid_location or state.mid_range:
        return TradeDecision(Decision.NO_TRADE, direction, NoTradeReason.MID_RANGE, None, None, None)

    # v1 continuation model requires OI expansion in either direction.
    if state.oi_change <= 0 or state.oi_percentile < config.oi_percentile_threshold:
        return TradeDecision(Decision.NO_TRADE, direction, NoTradeReason.OI_INSUFFICIENT, None, None, None)

    if _positioning_contradicts(direction, state.legal_net_delta, state.retail_net_delta):
        return TradeDecision(
            Decision.NO_TRADE, direction, NoTradeReason.POSITIONING_CONTRADICTION, None, None, None
        )

    required_rvol = config.breakout_rvol_minimum if state.breakout_setup else config.rvol_minimum
    if state.rvol < required_rvol:
        return TradeDecision(Decision.NO_TRADE, direction, NoTradeReason.RVOL_LOW, None, None, None)

    if not state.trigger_confirmed:
        return TradeDecision(Decision.WAIT, direction, NoTradeReason.NO_TRIGGER, None, None, None)

    if state.atr <= 0:
        return TradeDecision(Decision.NO_TRADE, direction, NoTradeReason.DATA_QUALITY, None, None, None)

    if direction is Direction.LONG:
        stop = state.structural_stop - config.stop_buffer_atr * state.atr
        risk_distance = state.entry - stop
        reward_distance = state.nearest_target - state.entry
    else:
        stop = state.structural_stop + config.stop_buffer_atr * state.atr
        risk_distance = stop - state.entry
        reward_distance = state.entry - state.nearest_target

    if risk_distance <= 0 or reward_distance <= 0:
        return TradeDecision(Decision.NO_TRADE, direction, NoTradeReason.RR_INSUFFICIENT, stop, None, None)

    if risk_distance > config.max_stop_atr * state.atr:
        return TradeDecision(
            Decision.NO_TRADE,
            direction,
            NoTradeReason.STOP_TOO_WIDE,
            stop,
            risk_distance,
            reward_distance / risk_distance,
        )

    potential_rr = reward_distance / risk_distance
    if potential_rr < config.min_rr:
        return TradeDecision(
            Decision.NO_TRADE,
            direction,
            NoTradeReason.RR_INSUFFICIENT,
            stop,
            risk_distance,
            potential_rr,
        )

    if abs(state.entry - state.trigger_price) > config.max_late_entry_atr * state.atr:
        return TradeDecision(
            Decision.NO_TRADE,
            direction,
            NoTradeReason.LATE_ENTRY,
            stop,
            risk_distance,
            potential_rr,
        )

    return TradeDecision(Decision.TRADE_READY, direction, None, stop, risk_distance, potential_rr)
