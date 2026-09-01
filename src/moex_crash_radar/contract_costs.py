from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from urllib.parse import urlencode

from .moex import ISS_BASE, _get_json
from .public_baseline import Trade


@dataclass(frozen=True)
class ContractSpec:
    secid: str
    min_step: float
    step_price_rub: float
    broker_fee_rub_round_trip: float = 0.0
    slippage_ticks_round_trip: float = 1.0
    source: str = "MOEX_ISS"

    @property
    def rub_per_price_unit(self) -> float:
        return self.step_price_rub / self.min_step if self.min_step > 0 else 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def fetch_contract_spec(
    secid: str,
    *,
    broker_fee_rub_round_trip: float = 0.0,
    slippage_ticks_round_trip: float = 1.0,
) -> ContractSpec | None:
    """Read contract-specific price-step economics from MOEX ISS.

    Broker commission is intentionally external/configurable. MOEX market data
    can define tick geometry, but it cannot know the user's broker tariff.
    """
    params = {
        "iss.meta": "off",
        "iss.only": "securities",
        "securities.columns": "SECID,MINSTEP,STEPPRICE",
    }
    url = (
        f"{ISS_BASE}/engines/futures/markets/forts/securities/{secid}.json?"
        f"{urlencode(params)}"
    )
    payload = _get_json(url)
    block = payload.get("securities", {})
    columns = block.get("columns", [])
    rows = block.get("data", [])
    if not columns or not rows:
        return None
    row = dict(zip(columns, rows[0]))
    try:
        min_step = float(row["MINSTEP"])
        step_price = float(row["STEPPRICE"])
    except (KeyError, TypeError, ValueError):
        return None
    if min_step <= 0 or step_price <= 0:
        return None
    return ContractSpec(
        secid=secid,
        min_step=min_step,
        step_price_rub=step_price,
        broker_fee_rub_round_trip=float(broker_fee_rub_round_trip),
        slippage_ticks_round_trip=float(slippage_ticks_round_trip),
    )


def trade_cost_r(trade: Trade, spec: ContractSpec) -> float | None:
    risk_distance = abs(trade.entry - trade.stop)
    risk_rub = risk_distance * spec.rub_per_price_unit
    if risk_rub <= 0:
        return None
    execution_rub = (
        spec.broker_fee_rub_round_trip
        + spec.slippage_ticks_round_trip * spec.step_price_rub
    )
    return execution_rub / risk_rub


def apply_contract_cost(trade: Trade, spec: ContractSpec) -> Trade:
    cost_r = trade_cost_r(trade, spec)
    if cost_r is None:
        return trade
    return replace(
        trade,
        cost_r=round(cost_r, 4),
        net_r=round(trade.gross_r - cost_r, 4),
    )
