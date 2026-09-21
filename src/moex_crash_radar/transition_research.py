"""Locked R1.5.3-B historical research helpers.

This module is deliberately analysis-only. It neither reads live data nor
changes Crash Score, EXIT Gate, state, actions, or dashboard output.
"""
from __future__ import annotations

from collections.abc import Sequence

from .history import DailyEvidence

MODELS = ("M0", "M1", "M2", "M3", "M4")

def model_observations(row: DailyEvidence, prior_five_session_return_pct: float | None) -> dict[str, bool | None]:
    """Return locked observations; None means insufficient point-in-time data."""
    required = (prior_five_session_return_pct, row.market_structure_score, row.breadth_score, row.volume_distribution_score, row.volatility_liquidity_score)
    if row.coverage < 0.70 or any(value is None for value in required):
        return {model: None for model in MODELS}
    price = row.market_structure_score < 50 and prior_five_session_return_pct > -3.0
    breadth = row.breadth_score >= 40
    volume = row.volume_distribution_score >= 40
    volatility = row.volatility_liquidity_score >= 50
    return {"M0": price, "M1": price and breadth, "M2": price and breadth and volume, "M3": price and breadth and volatility, "M4": price and breadth and (volume or volatility)}

def future_drawdown_pct(rows: Sequence[DailyEvidence], index: int, horizon: int = 20) -> float | None:
    """Evaluation-only forward outcome, unavailable without a complete horizon."""
    future = rows[index + 1 : index + 1 + horizon]
    if len(future) != horizon:
        return None
    return round((min(row.close for row in future) / rows[index].close - 1.0) * 100.0, 4)

def summarize_model(rows: Sequence[DailyEvidence], model: str, *, start: str, end: str) -> dict[str, int | float | None]:
    usable = alerts = outcomes = true_positive = false_positive = false_negative = 0
    longest_persistence = current_persistence = 0
    lead_sessions: list[int] = []
    for i, row in enumerate(rows):
        if not start <= row.day <= end:
            continue
        outcome_dd = future_drawdown_pct(rows, i)
        if outcome_dd is None:
            continue
        five_day_return = None if i < 5 else (row.close / rows[i - 5].close - 1.0) * 100.0
        alert = model_observations(row, five_day_return)[model]
        if alert is None:
            current_persistence = 0
            continue
        usable += 1
        outcome = outcome_dd <= -8.0
        outcomes += int(outcome)
        if alert:
            alerts += 1
            current_persistence += 1
            longest_persistence = max(longest_persistence, current_persistence)
            if outcome:
                true_positive += 1
                lead_sessions.append(next(j for j in range(1, 21) if rows[i + j].close <= rows[i].close * 0.92))
            else:
                false_positive += 1
        else:
            current_persistence = 0
            false_negative += int(outcome)
    precision = true_positive / alerts if alerts else None
    recall = true_positive / outcomes if outcomes else None
    false_alarm_rate = false_positive / alerts if alerts else None
    return {"usable_rows": usable, "alert_rows": alerts, "outcome_rows": outcomes, "true_positive_rows": true_positive, "false_positive_rows": false_positive, "false_negative_rows": false_negative, "precision": round(precision, 4) if precision is not None else None, "recall": round(recall, 4) if recall is not None else None, "false_alarm_rate": round(false_alarm_rate, 4) if false_alarm_rate is not None else None, "median_lead_sessions": sorted(lead_sessions)[len(lead_sessions) // 2] if lead_sessions else None, "max_persistence_sessions": longest_persistence}
