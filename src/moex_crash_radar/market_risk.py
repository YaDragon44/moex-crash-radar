from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

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


@dataclass(frozen=True)
class IndependentMarketRiskInputs:
    """R0.9 market-only risk inputs.

    These are direct market stress groups. Crowd, Context, Positioning and the
    frozen Crash/EXIT result are deliberately excluded from this path.
    """

    market_structure: float | None = None
    breadth: float | None = None
    volatility_liquidity: float | None = None
    volume_distribution: float | None = None


@dataclass(frozen=True)
class IndependentMarketRiskResult:
    score: float | None
    state: MarketRisk
    coverage: float
    available_groups: int
    velocity: float | None
    direction: str
    reasons: tuple[str, ...]


FRAGILITY_WEIGHTS = {
    "valuation": 0.30,
    "concentration": 0.30,
    "leverage": 0.25,
    "macro_credit": 0.15,
}

# R0.9 candidate research weights. They intentionally differ from CRASH_WEIGHTS
# and use market-only evidence. Historical validation is required before any
# production/action use.
INDEPENDENT_RISK_WEIGHTS: Mapping[str, float] = {
    "market_structure": 0.30,
    "breadth": 0.30,
    "volatility_liquidity": 0.25,
    "volume_distribution": 0.15,
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


def calculate_independent_market_risk(
    inputs: IndependentMarketRiskInputs,
    *,
    prior_score: float | None = None,
) -> IndependentMarketRiskResult:
    values = {
        "market_structure": inputs.market_structure,
        "breadth": inputs.breadth,
        "volatility_liquidity": inputs.volatility_liquidity,
        "volume_distribution": inputs.volume_distribution,
    }
    for value in values.values():
        if value is not None:
            _bounded(value)

    available = {k: v for k, v in values.items() if v is not None}
    available_weight = sum(INDEPENDENT_RISK_WEIGHTS[k] for k in available)
    groups = len(available)
    if groups < 3 or available_weight < 0.70:
        return IndependentMarketRiskResult(
            None,
            MarketRisk.DATA_INSUFFICIENT,
            round(available_weight, 4),
            groups,
            None,
            "N/A",
            (),
        )

    score = round(
        sum(float(available[k]) * INDEPENDENT_RISK_WEIGHTS[k] for k in available) / available_weight,
        2,
    )
    velocity = None if prior_score is None else round(score - prior_score, 2)
    if velocity is None:
        direction = "N/A"
    elif velocity >= 5:
        direction = "RISING_FAST"
    elif velocity >= 1.5:
        direction = "RISING"
    elif velocity <= -5:
        direction = "FALLING_FAST"
    elif velocity <= -1.5:
        direction = "FALLING"
    else:
        direction = "STABLE"

    labels = {
        "market_structure": "market structure stress",
        "breadth": "breadth deterioration",
        "volatility_liquidity": "volatility/liquidity stress",
        "volume_distribution": "distribution pressure",
    }
    ranked = sorted(available.items(), key=lambda item: item[1], reverse=True)
    reasons = tuple(labels[key] for key, value in ranked[:3] if value >= 50)

    return IndependentMarketRiskResult(
        score=score,
        state=market_risk_state(score),
        coverage=round(available_weight, 4),
        available_groups=groups,
        velocity=velocity,
        direction=direction,
        reasons=reasons,
    )


def calculate_market_risk(
    crash: CrashResult,
    context: ContextResult,
    fragility: FragilityResult,
) -> MarketRiskResult:
    """Legacy research composite retained for backward compatibility.

    R0.9 historical validation uses ``calculate_independent_market_risk`` and
    does not consume this legacy Crash-dependent composite.
    """
    if crash.score is None or crash.quality not in {DataQuality.LIVE, DataQuality.DELAYED}:
        return MarketRiskResult(None, MarketRisk.DATA_INSUFFICIENT, DataQuality.NA, None, None, None, ("Crash/market data unavailable",))

    components: list[tuple[str, float, float]] = [("market", crash.score, 0.60)]
    if context.score is not None and context.quality in {DataQuality.LIVE, DataQuality.DELAYED}:
        components.append(("context", context.score, 0.25))
    if fragility.score is not None:
        components.append(("fragility", fragility.score, 0.15))

    available_weight = sum(weight for _, _, weight in components)
    score = round(sum(value * weight for _, value, weight in components) / available_weight, 2)
    state = market_risk_state(score)

    reasons: list[str] = [f"Market deterioration {crash.score:.1f}/100"]
    reasons.append(f"External context stress {context.score:.1f}/100" if context.score is not None else "Context N/A")
    reasons.append(f"Structural fragility {fragility.score:.1f}/100" if fragility.score is not None else "Fragility N/A")

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
