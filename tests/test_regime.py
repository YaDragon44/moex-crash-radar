from moex_crash_radar.regime import MarketRegime, RegimeInputs, classify_regime


def test_incomplete_evidence_fails_closed():
    r = classify_regime(RegimeInputs(None, "NORMAL", 0, 1.0))
    assert r.regime == MarketRegime.DATA_INSUFFICIENT


def test_low_crash_no_confirmations_is_risk_on():
    r = classify_regime(RegimeInputs(20, "NORMAL", 0, 2.0, "GREED", "RISING"))
    assert r.regime == MarketRegime.RISK_ON
    assert r.crowd_context == "GREED / RISING"


def test_crowd_euphoria_does_not_create_overheated_regime():
    r = classify_regime(RegimeInputs(20, "NORMAL", 0, 2.0, "EUPHORIA", "RISING_FAST"))
    assert r.regime == MarketRegime.RISK_ON


def test_early_warning_creates_distribution_watch_not_distribution():
    r = classify_regime(RegimeInputs(58, "EARLY_WARNING", 1, -1.0))
    assert r.regime == MarketRegime.NEUTRAL
    assert "DISTRIBUTION WATCH" in r.transition


def test_exit_watch_maps_to_distribution():
    r = classify_regime(RegimeInputs(66, "EXIT_WATCH", 2, -2.0))
    assert r.regime == MarketRegime.DISTRIBUTION


def test_validated_exit_has_precedence():
    r = classify_regime(RegimeInputs(70, "CASH_CONFIRMED", 3, -4.0))
    assert r.regime == MarketRegime.RISK_OFF


def test_reentry_regimes_are_not_inferred():
    r = classify_regime(RegimeInputs(10, "NORMAL", 0, 5.0, "PANIC", "RISING_FAST"))
    assert r.regime == MarketRegime.RISK_ON
    assert r.regime not in {MarketRegime.CAPITULATION, MarketRegime.ACCUMULATION, MarketRegime.RECOVERY}
