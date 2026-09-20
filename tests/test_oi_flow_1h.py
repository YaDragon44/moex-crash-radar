from moex_crash_radar.oi_flow_1h import (
    Decision,
    Direction,
    NoTradeReason,
    OIFlowConfig,
    Regime,
    SignalSnapshot,
    evaluate_signal,
)


def base_snapshot(**overrides):
    values = dict(
        data_ready=True,
        regime=Regime.BULL,
        valid_location=True,
        oi_expanding=True,
        oi_percentile=80.0,
        positioning_contradiction=False,
        rvol=1.3,
        breakout_setup=False,
        trigger_confirmed=True,
        stop_distance_atr=1.0,
        potential_rr=2.5,
        entry_distance_atr=0.2,
    )
    values.update(overrides)
    return SignalSnapshot(**values)


def test_long_trade_ready():
    result = evaluate_signal(base_snapshot())
    assert result.decision is Decision.TRADE_READY
    assert result.direction is Direction.LONG
    assert result.reason is None


def test_bear_maps_to_short():
    result = evaluate_signal(base_snapshot(regime=Regime.BEAR))
    assert result.decision is Decision.TRADE_READY
    assert result.direction is Direction.SHORT


def test_fail_closed_on_data_quality():
    result = evaluate_signal(base_snapshot(data_ready=False, regime=Regime.BEAR))
    assert result.decision is Decision.NO_TRADE
    assert result.direction is None
    assert result.reason is NoTradeReason.DATA_QUALITY


def test_range_is_no_trade():
    result = evaluate_signal(base_snapshot(regime=Regime.RANGE))
    assert result.reason is NoTradeReason.RANGE


def test_oi_threshold_is_inclusive():
    cfg = OIFlowConfig(oi_percentile_min=75.0)
    result = evaluate_signal(base_snapshot(oi_percentile=75.0), cfg)
    assert result.decision is Decision.TRADE_READY


def test_oi_below_threshold_rejected():
    result = evaluate_signal(base_snapshot(oi_percentile=74.99))
    assert result.reason is NoTradeReason.OI_INSUFFICIENT


def test_breakout_requires_stronger_rvol():
    result = evaluate_signal(base_snapshot(breakout_setup=True, rvol=1.1))
    assert result.reason is NoTradeReason.RVOL_LOW


def test_no_trigger_waits_instead_of_entering():
    result = evaluate_signal(base_snapshot(trigger_confirmed=False))
    assert result.decision is Decision.WAIT
    assert result.reason is NoTradeReason.NO_TRIGGER


def test_risk_gates_execute_after_trigger():
    too_wide = evaluate_signal(base_snapshot(stop_distance_atr=1.51))
    assert too_wide.reason is NoTradeReason.STOP_TOO_WIDE

    poor_rr = evaluate_signal(base_snapshot(potential_rr=1.99))
    assert poor_rr.reason is NoTradeReason.RR_INSUFFICIENT

    late = evaluate_signal(base_snapshot(entry_distance_atr=0.51))
    assert late.reason is NoTradeReason.LATE_ENTRY


def test_gate_order_is_fail_closed():
    result = evaluate_signal(
        base_snapshot(
            valid_location=False,
            oi_expanding=False,
            trigger_confirmed=False,
            potential_rr=0.1,
        )
    )
    assert result.reason is NoTradeReason.MID_RANGE
