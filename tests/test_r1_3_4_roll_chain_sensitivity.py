from moex_crash_radar.contract_costs import ContractSpec, trade_cost_r
from moex_crash_radar.moex import Candle
from moex_crash_radar.public_baseline import BaselineConfig, Trade
from moex_crash_radar.risk_sensitivity import assess_plateau, chronological_splits, sensitivity_grid
from moex_crash_radar.roll_chain import RollBar, active_contract_for_day, quarterly_contracts


def _candle(ts: str, price: float = 100.0, volume: float = 1000.0) -> Candle:
    return Candle(begin=ts, open=price, close=price + 0.2, high=price + 0.5, low=price - 0.5, value=None, volume=volume)


def test_quarterly_contract_ids_and_roll_dates_are_deterministic():
    chain = quarterly_contracts("SI", start="2026-01-01", end="2026-12-31", secid_prefix="Si", roll_business_days=5)
    ids = [c.secid for c in chain]
    assert "SiH6" in ids and "SiM6" in ids and "SiU6" in ids and "SiZ6" in ids
    h6 = next(c for c in chain if c.secid == "SiH6")
    assert h6.expiry == "2026-03-19"
    assert h6.roll_date < h6.expiry


def test_active_contract_changes_on_explicit_roll_boundary():
    chain = quarterly_contracts("MX", start="2026-01-01", end="2026-06-30", secid_prefix="MX", roll_business_days=5)
    h6 = next(c for c in chain if c.secid == "MXH6")
    m6 = next(c for c in chain if c.secid == "MXM6")
    from datetime import date, timedelta
    assert active_contract_for_day(date.fromisoformat(h6.roll_date), chain).secid == h6.secid
    assert active_contract_for_day(date.fromisoformat(h6.roll_date) + timedelta(days=1), chain).secid == m6.secid


def test_contract_cost_is_tick_based_not_quote_bps():
    trade = Trade(
        model="M0", direction="LONG", signal_time="2026-01-01 10:00:00", entry_time="2026-01-01 11:00:00",
        exit_time="2026-01-01 12:00:00", entry=100.0, stop=99.0, exit=102.0,
        gross_r=2.0, cost_r=0.0, net_r=2.0, exit_reason="TARGET_2R",
    )
    spec = ContractSpec(secid="X", min_step=0.5, step_price_rub=10.0, broker_fee_rub_round_trip=5.0, slippage_ticks_round_trip=2.0)
    # 1 quote point risk = 20 RUB; costs = 5 + 2*10 = 25 RUB => 1.25R.
    assert trade_cost_r(trade, spec) == 1.25


def test_chronological_split_is_ordered_and_exhaustive():
    bars = tuple(RollBar(_candle(f"2026-01-{1 + i // 8:02d} {10 + i % 8:02d}:00:00"), "MXH6", "MX", "2026-03-19") for i in range(100))
    split = chronological_splits(bars)
    assert len(split["IS"]) == 60
    assert len(split["VALIDATION"]) == 20
    assert len(split["OOS"]) == 20
    assert split["IS"][-1].candle.begin < split["VALIDATION"][0].candle.begin < split["OOS"][0].candle.begin


def test_sensitivity_grid_is_broad_not_best_point_selector():
    bars = []
    price = 100.0
    for i in range(160):
        day = 1 + i // 8
        hour = 10 + i % 8
        open_ = price
        drift = 0.45 if (i // 32) % 2 == 0 else -0.40
        close = open_ + drift + (-0.55 if i % 6 == 0 else 0.0)
        candle = Candle(
            begin=f"2026-01-{day:02d} {hour:02d}:00:00", open=open_, close=close,
            high=max(open_, close) + 0.3, low=min(open_, close) - 0.3, value=None,
            volume=1200 + (800 if i % 7 == 0 else 0),
        )
        bars.append(RollBar(candle, "MXH6", "MX", "2026-03-19"))
        price = close
    points = sensitivity_grid(
        bars, models=("M0",), max_stop_atrs=(1.25, 1.5), min_rrs=(1.5, 2.0),
        base_config=BaselineConfig(rvol_sessions=3),
    )
    assert len(points) == 4
    assessment = assess_plateau(points, "M0", min_trades=999)
    assert assessment.stable_positive is False
    assert assessment.reason == "NO_POSITIVE_POINTS_WITH_MIN_SAMPLE"
