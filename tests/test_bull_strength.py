from moex_crash_radar.bull_strength import BullInputs, BullState, bull_bubble_regime, calculate_bull_strength


def test_bull_strength_fails_closed():
    r = calculate_bull_strength(BullInputs(trend=90, momentum=80))
    assert r.score is None
    assert r.state == BullState.DATA_INSUFFICIENT


def test_strong_bull_detected():
    r = calculate_bull_strength(BullInputs(85, 80, 82, 75, 78))
    assert r.score is not None and r.score >= 75
    assert r.state == BullState.VERY_STRONG


def test_healthy_strong_bull_is_not_dangerous_bubble():
    assert bull_bubble_regime(82, 28) == "HEALTHY_STRONG_BULL"


def test_strong_bull_can_coexist_with_bubble():
    assert bull_bubble_regime(84, 76) == "BULL_WITH_BUBBLE_BUILD_UP"


def test_weakening_bull_with_extreme_bubble_is_distribution_watch():
    assert bull_bubble_regime(55, 85) == "FRAGILE_BULL_DISTRIBUTION_WATCH"


def test_broken_bull_with_bubble_is_breakdown_risk():
    assert bull_bubble_regime(25, 82) == "BUBBLE_BREAKDOWN_RISK"
