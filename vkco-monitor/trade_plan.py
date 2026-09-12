from __future__ import annotations

import math
import os
from typing import Any


def _env_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    value = float(raw.replace(",", "."))
    return value if value > 0 else None


def build_trade_plan(signal: dict[str, Any], lot_size: int = 1) -> dict[str, Any]:
    entry = float(signal["entry"])
    stop = float(signal["stop"])
    if entry <= stop:
        raise ValueError("Для LONG Entry должен быть выше Stop")

    unit_risk = entry - stop
    capital = _env_float("TRADING_CAPITAL_RUB")
    risk_pct = _env_float("RISK_PCT")

    plan: dict[str, Any] = {
        "unit_risk": round(unit_risk, 2),
        "capital": capital,
        "risk_pct": risk_pct,
        "allowed_risk": None,
        "shares": None,
        "lots": None,
        "position_value": None,
        "actual_risk": None,
        "sizing_ready": False,
    }

    if capital is None or risk_pct is None:
        return plan

    allowed_risk = capital * risk_pct / 100.0
    raw_shares = math.floor(allowed_risk / unit_risk)
    shares = (raw_shares // lot_size) * lot_size
    if shares <= 0:
        return plan

    plan.update({
        "allowed_risk": round(allowed_risk, 2),
        "shares": shares,
        "lots": shares // lot_size,
        "position_value": round(shares * entry, 2),
        "actual_risk": round(shares * unit_risk, 2),
        "sizing_ready": True,
    })
    return plan


def format_trade_plan(signal: dict[str, Any]) -> str:
    p = build_trade_plan(signal)
    if not p["sizing_ready"]:
        return (
            f"Риск на 1 акцию: {p['unit_risk']:.2f} ₽\n"
            "Размер позиции: не рассчитан — задайте GitHub Variables "
            "TRADING_CAPITAL_RUB и RISK_PCT."
        )

    return (
        f"Капитал для расчёта: {p['capital']:,.0f} ₽\n"
        f"Риск на сделку: {p['risk_pct']:.2f}% = {p['allowed_risk']:,.0f} ₽\n"
        f"Риск на 1 акцию: {p['unit_risk']:.2f} ₽\n"
        f"Размер позиции: {p['shares']} акций / {p['lots']} лотов\n"
        f"Стоимость позиции: ~{p['position_value']:,.0f} ₽\n"
        f"Фактический риск: ~{p['actual_risk']:,.0f} ₽"
    )
