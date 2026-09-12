from moex_crash_radar.reentry import ReentryInputs, ReentryState, classify_reentry


def test_missing_data_fails_closed():
    r = classify_reentry(ReentryInputs(None, 40, 0, 4, -20))
    assert r.state == ReentryState.DATA_INSUFFICIENT
    assert r.production_ready is False


def test_no_recent_exit_means_inactive():
    r = classify_reentry(ReentryInputs(61, 20, 0, 5, -20))
    assert r.state == ReentryState.INACTIVE


def test_capitulation_watch_requires_extreme_selloff():
    r = classify_reentry(ReentryInputs(10, 80, 3, -6, 5))
    assert r.state == ReentryState.CAPITULATION_WATCH


def test_accumulation_watch_requires_falling_stress_and_stabilization():
    r = classify_reentry(ReentryInputs(20, 55, 2, 1, -18))
    assert r.state == ReentryState.ACCUMULATION_WATCH


def test_recovery_watch_requires_low_stress_and_rebound():
    r = classify_reentry(ReentryInputs(30, 40, 1, 4, -12))
    assert r.state == ReentryState.RECOVERY_WATCH


def test_reentry_is_never_production_ready_in_r11():
    r = classify_reentry(ReentryInputs(30, 40, 1, 4, -12))
    assert r.production_ready is False
