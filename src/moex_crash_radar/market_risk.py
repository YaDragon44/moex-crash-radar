from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .context import ContextResult
from .engine import CrashResult, DataQuality


class MarketRisk(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


class FragilityState(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


@dataclass(frozen=True)
class FragilityInput:
    """Slow structural vulnerability inputs.

    All values are relative 0..100 stress scores. They are deliberately kept
    outside the calibrated Crash/EXIT score. Missing inputs are allowed; the
    layer fails closed unless at least two independent groups are available.
    """

    valuation: float | None = None
    concentration: float | None = None
    leverage: float | None = None
    macro_credit: float | None = None


@dataclass(frozen=True)
class FragilityResult:
    score: float | None
    state: FragilityState
    coverage: float
    available_groups: int


@dataclass(frozen=True)
class MarketRiskResult:
    score: float | None
    state: MarketRisk
    quality: DataQuality
    crash_component: float | None
    context_component: float | None
    fragility_component: float | None
    reasons: tuple[str, ...]


FRAGILITY_WEIGHTS = {
    "valuation": 0.30,
    "concentration": 0.30,
    "leverage": 0.25,
    "macro_credit": 0.15,
}


def _bounded(value: float) -> float:
    if not 0 <= value <= 100:
        raise ValueError("risk input must be in [0, 100]")
    return value


def calculate_fragility(inputs: FragilityInput) -> FragilityResult:
    weighted = 0.0
    available_weight = 0.0
    groups = 0
    for key, weight in FRAGILITY_WEIGHTS.items():
        value = getattr(inputs, key)
        if value is None:
            continue
        weighted += _bounded(value) * weight
        available_weight += weight
        groups += 1

    if groups < 2 or available_weight < 0.50:
        return FragilityResult(None, FragilityState.DATA_INSUFFICIENT, round(available_weight, 4), groups)

    score = round(weighted / available_weight, 2)
    if score < 30:
        state = FragilityState.LOW
    elif score < 55:
        state = FragilityState.MODERATE
    elif score < 75:
        state = FragilityState.HIGH
    else:
        state = FragilityState.EXTREME
    return FragilityResult(score, state, round(available_weight, 4), groups)


def market_risk_state(score: float) -> MarketRisk:
    if score < 25:
        return MarketRisk.LOW
    if score < 45:
        return MarketRisk.MODERATE
    if score < 60:
        return MarketRisk.ELEVATED
    if score < 75:
        return MarketRisk.HIGH
    return MarketRisk.CRITICAL


def calculate_market_risk(
    crash: CrashResult,
    context: ContextResult,
    fragility: FragilityResult,
) -> MarketRiskResult:
    """Independent Market Risk composite for capital decisions.

    Crash/market deterioration is the fast component. Context is an external
    confirmation layer. Fragility is slow structural vulnerability. This
    function does not mutate or re-calibrate Crash Score or the EXIT Gate.

    Until historical R0.5.4 validation is complete the weights are candidate
    research weights, not production-calibrated probabilities or thresholds.
    """
    if crash.score is None or crash.quality not in {DataQuality.LIVE, DataQuality.DELAYED}:
        return MarketRiskResult(None, MarketRisk.DATA_INSUFFICIENT, DataQuality.NA, None, None, None, ("Crash/market data unavailable",))

    components: list[tuple[str, float, float]] = [("market", crash.score, 0.60)]
    if context.score is not None and context.quality in {DataQuality.LIVE, DataQuality.DELAYED}:
        components.append(("context", context.score, 0.25))
    if fragility.score is not None:
        components.append(("fragility", fragility.score, 0.15))

    available_weight = sum(weight for _, _, weight in components)
    # Risk may be shown with market-only evidence, but is actionable only after
    # downstream Quality/Action Gate confirms sufficient independent coverage.
    score = round(sum(value * weight for _, value, weight in components) / available_weight, 2)
    state = market_risk_state(score)

    reasons: list[str] = []
    reasons.append(f"Market deterioration {crash.score:.1f}/100")
    if context.score is not None:
        reasons.append(f"External context stress {context.score:.1f}/100")
    else:
        reasons.append("Context N/A")
    if fragility.score is not None:
        reasons.append(f"Structural fragility {fragility.score:.1f}/100")
    else:
        reasons.append("Fragility N/A")

    quality = DataQuality.DELAYED if (
        crash.quality == DataQuality.DELAYED or context.quality == DataQuality.DELAYED
    ) else DataQuality.LIVE
    return MarketRiskResult(
        score=score,
        state=state,
        quality=quality,
        crash_component=crash.score,
        context_component=context.score,
        fragility_component=fragility.score,
        reasons=tuple(reasons[:3]),
    )
