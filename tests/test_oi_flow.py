from moex_crash_radar.oi_flow import (
    Decision,
    Direction,
    NoTradeReason,
    Regime,
    SignalState,
    evaluate_signal,
)


def base_state(**overrides):
    data = dict(
        quality_ready=True,
        regime=Regime.BULL,
        valid_location=True,
        mid_range=False,
        oi_change=5.0,
        oi_percentile=85.0,
        legal_net_delta=10.0,
        retail_net_delta=-8.0,
        rvol=1.35,
        trigger_confirmed=True,
        breakout_setup=False,
        atr=10.0,
        entry=110.0,
        structural_stop=100.0,
        nearest_target=140.0,
        trigger_price=109.0,
    )
    data.update(overrides)
    return SignalState(**data)


def test_long_trade_ready_when_all_gates_pass():
    result = evaluate_signal(base_state())
    assert result.decision is Decision.TRADE_READY
    assert result.direction is Direction.LONG
    assert result.reason is None
    assert result.stop == 98.0
    assert result.potential_rr == 2.5


def test_range_is_hard_no_trade():
    result = evaluate_signal(base_state(regime=Regime.RANGE))
    assert result.decision is Decision.NO_TRADE
    assert result.reason is NoTradeReason.RANGE


def test_oi_contraction_is_no_trade():
    result = evaluate_signal(base_state(oi_change=-2.0))
    assert result.reason is NoTradeReason.OI_INSUFFICIENT


def test_positioning_only_vetoes_on_joint_contradiction():
    one_group = evaluate_signal(base_state(legal_net_delta=-2.0, retail_net_delta=-5.0))
    assert one_group.decision is Decision.TRADE_READY

    both = evaluate_signal(base_state(legal_net_delta=-2.0, retail_net_delta=5.0))
    assert both.decision is Decision.NO_TRADE
    assert both.reason is NoTradeReason.POSITIONING_CONTRADICTION


def test_breakout_requires_higher_rvol():
    result = evaluate_signal(base_state(breakout_setup=True, rvol=1.1))
    assert result.reason is NoTradeReason.RVOL_LOW


def test_missing_trigger_waits_instead_of_forcing_trade():
    result = evaluate_signal(base_state(trigger_confirmed=False))
    assert result.decision is Decision.WAIT
    assert result.reason is NoTradeReason.NO_TRIGGER


def test_stop_too_wide_rejects_otherwise_good_setup():
    result = evaluate_signal(base_state(structural_stop=90.0))
    assert result.reason is NoTradeReason.STOP_TOO_WIDE


def test_poor_rr_rejects_otherwise_good_setup():
    result = evaluate_signal(base_state(nearest_target=125.0))
    assert result.reason is NoTradeReason.RR_INSUFFICIENT


def test_late_entry_rejected():
    result = evaluate_signal(base_state(trigger_price=100.0))
    assert result.reason is NoTradeReason.LATE_ENTRY


def test_short_logic_is_symmetric():
    result = evaluate_signal(
        base_state(
            regime=Regime.BEAR,
            legal_net_delta=-10.0,
            retail_net_delta=8.0,
            entry=100.0,
            structural_stop=110.0,
            nearest_target=70.0,
            trigger_price=101.0,
        )
    )
    assert result.decision is Decision.TRADE_READY
    assert result.direction is Direction.SHORT
    assert result.stop == 112.0
    assert result.potential_rr == 2.5
