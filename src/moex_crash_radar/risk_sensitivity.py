from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from statistics import median
from typing import Iterable, Sequence

from .contract_costs import ContractSpec, apply_contract_cost
from .public_baseline import BaselineConfig, Trade, run_model, summarize
from .roll_chain import RollBar


@dataclass(frozen=True)
class SensitivityPoint:
    model: str
    max_stop_atr: float
    min_rr: float
    trades: int
    expectancy_r: float | None
    profit_factor: float | None
    max_drawdown_r: float | None
    total_net_r: float
    cost_coverage_pct: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlateauAssessment:
    model: str
    points: int
    positive_points: int
    min_trades_across_positive: int | None
    median_expectancy_positive_r: float | None
    stable_positive: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _segments(bars: Sequence[RollBar]) -> list[tuple[str, list]]:
    out: list[tuple[str, list]] = []
    active: str | None = None
    candles: list = []
    for row in bars:
        if active is None:
            active = row.secid
        if row.secid != active:
            out.append((active, candles))
            active, candles = row.secid, []
        candles.append(row.candle)
    if active is not None and candles:
        out.append((active, candles))
    return out


def run_roll_aware_model(
    bars: Sequence[RollBar],
    model: str,
    config: BaselineConfig,
    *,
    specs: dict[str, ContractSpec] | None = None,
) -> tuple[list[Trade], float]:
    """Run each contract segment independently to avoid roll-gap leakage."""
    specs = specs or {}
    trades: list[Trade] = []
    priced = 0
    for secid, candles in _segments(bars):
        # Legacy quote-bps costs are disabled. R1.3.4 applies execution costs
        # from contract tick economics after each segment backtest.
        gross_config = replace(config, fee_bps_round_trip=0.0, slippage_bps_round_trip=0.0)
        segment_trades = run_model(candles, model, gross_config)
        spec = specs.get(secid)
        if spec is not None:
            segment_trades = [apply_contract_cost(t, spec) for t in segment_trades]
            priced += len(segment_trades)
        trades.extend(segment_trades)
    coverage = (100.0 * priced / len(trades)) if trades else 100.0
    return trades, coverage


def sensitivity_grid(
    bars: Sequence[RollBar],
    *,
    models: Iterable[str] = ("M0", "M1", "M5"),
    max_stop_atrs: Iterable[float] = (1.25, 1.5, 1.75, 2.0),
    min_rrs: Iterable[float] = (1.5, 1.75, 2.0, 2.25),
    base_config: BaselineConfig = BaselineConfig(),
    specs: dict[str, ContractSpec] | None = None,
) -> list[SensitivityPoint]:
    points: list[SensitivityPoint] = []
    for model in models:
        for stop_atr in max_stop_atrs:
            for min_rr in min_rrs:
                config = replace(base_config, max_stop_atr=float(stop_atr), min_rr=float(min_rr))
                trades, coverage = run_roll_aware_model(bars, model, config, specs=specs)
                summary = summarize(model, trades)
                points.append(SensitivityPoint(
                    model=model,
                    max_stop_atr=float(stop_atr),
                    min_rr=float(min_rr),
                    trades=summary.trades,
                    expectancy_r=summary.expectancy_r,
                    profit_factor=summary.profit_factor,
                    max_drawdown_r=summary.max_drawdown_r,
                    total_net_r=summary.total_net_r,
                    cost_coverage_pct=round(coverage, 2),
                ))
    return points


def assess_plateau(
    points: Sequence[SensitivityPoint],
    model: str,
    *,
    min_trades: int = 30,
    min_positive_share: float = 0.60,
) -> PlateauAssessment:
    subset = [p for p in points if p.model == model]
    positive = [p for p in subset if p.trades >= min_trades and p.expectancy_r is not None and p.expectancy_r > 0]
    share = (len(positive) / len(subset)) if subset else 0.0
    stable = bool(subset) and share >= min_positive_share
    if not subset:
        reason = "NO_POINTS"
    elif not positive:
        reason = "NO_POSITIVE_POINTS_WITH_MIN_SAMPLE"
    elif not stable:
        reason = f"POSITIVE_SHARE_{share:.2f}_BELOW_{min_positive_share:.2f}"
    else:
        reason = "BROAD_POSITIVE_PLATEAU"
    return PlateauAssessment(
        model=model,
        points=len(subset),
        positive_points=len(positive),
        min_trades_across_positive=min((p.trades for p in positive), default=None),
        median_expectancy_positive_r=(round(median([p.expectancy_r for p in positive if p.expectancy_r is not None]), 4) if positive else None),
        stable_positive=stable,
        reason=reason,
    )


def chronological_splits(bars: Sequence[RollBar]) -> dict[str, tuple[RollBar, ...]]:
    """Deterministic 60/20/20 chronological IS / validation / OOS split."""
    n = len(bars)
    a = int(n * 0.60)
    b = int(n * 0.80)
    return {
        "IS": tuple(bars[:a]),
        "VALIDATION": tuple(bars[a:b]),
        "OOS": tuple(bars[b:]),
    }
