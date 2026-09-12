from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MarketRegime(str, Enum):
    RISK_ON = "RISK-ON"
    RISK_ON_OVERHEATED = "RISK-ON / OVERHEATED"
    NEUTRAL = "NEUTRAL"
    DISTRIBUTION = "DISTRIBUTION"
    RISK_OFF = "RISK-OFF"
    PANIC = "PANIC"
    CAPITULATION = "CAPITULATION"
    ACCUMULATION = "ACCUMULATION"
    RECOVERY = "RECOVERY"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


@dataclass(frozen=True)
class RegimeInputs:
    """R1.0 inputs. Only validated production-safe facts may drive a regime.

    Crowd is explanatory/shadow only after R0.8.3 NO_INCREMENTAL_VALUE.
    Vulnerability is unavailable after R0.9.2 DATA_INSUFFICIENT.
    Re-entry states remain disabled until R1.1 validation.
    """
    crash_score: float | None
    exit_stage: str | None
    confirmations: int | None
    return_5d_pct: float | None
    crowd_state: str | None = None
    crowd_direction: str | None = None


@dataclass(frozen=True)
class RegimeResult:
    regime: MarketRegime
    transition: str
    confidence: str
    reasons: tuple[str, ...]
    crowd_context: str | None


def classify_regime(inputs: RegimeInputs) -> RegimeResult:
    if inputs.crash_score is None or inputs.exit_stage is None or inputs.confirmations is None:
        return RegimeResult(
            MarketRegime.DATA_INSUFFICIENT,
            "N/A",
            "LOW",
            ("production crash/exit evidence incomplete",),
            None,
        )

    score = float(inputs.crash_score)
    confirmations = int(inputs.confirmations)
    ret5 = inputs.return_5d_pct
    stage = str(inputs.exit_stage).upper()
    crowd_context = None
    if inputs.crowd_state:
        crowd_context = str(inputs.crowd_state)
        if inputs.crowd_direction:
            crowd_context += f" / {inputs.crowd_direction}"

    # EXIT stage has precedence because it is the historically validated gate.
    if stage in {"CASH_CONFIRMED", "EXIT_CONFIRMED"} and score >= 65:
        return RegimeResult(MarketRegime.RISK_OFF, "RISK-OFF CONFIRMED", "HIGH",
                            ("validated EXIT gate confirmed", "crash score >= 65"), crowd_context)

    if score >= 75 and confirmations >= 3 and ret5 is not None and ret5 <= -5:
        return RegimeResult(MarketRegime.PANIC, "RISK-OFF → PANIC WATCH", "HIGH",
                            ("extreme current crash stress", "3+ confirmations", "5d selloff <= -5%"), crowd_context)

    if stage == "EXIT_WATCH" or (score >= 65 and confirmations >= 2):
        return RegimeResult(MarketRegime.DISTRIBUTION, "DISTRIBUTION → RISK-OFF WATCH", "MEDIUM",
                            ("EXIT conditions building", "elevated crash stress"), crowd_context)

    if stage == "EARLY_WARNING" or score >= 56:
        return RegimeResult(MarketRegime.NEUTRAL, "RISK-ON → DISTRIBUTION WATCH", "MEDIUM",
                            ("early-warning threshold reached",), crowd_context)

    # We deliberately do not infer OVERHEATED from euphoria alone: Crowd did not
    # prove incremental crash value. Nor do we infer recovery/capitulation here.
    if score < 35 and confirmations == 0:
        return RegimeResult(MarketRegime.RISK_ON, "STABLE / NO EXIT PRESSURE", "MEDIUM",
                            ("low current crash stress", "no EXIT confirmations"), crowd_context)

    return RegimeResult(MarketRegime.NEUTRAL, "NO CONFIRMED TRANSITION", "MEDIUM",
                        ("mixed current crash evidence",), crowd_context)
