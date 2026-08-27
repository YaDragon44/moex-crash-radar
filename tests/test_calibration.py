from moex_crash_radar.calibration import false_event_stats, signal_event_indices
from moex_crash_radar.history import DailyEvidence


def row(day, close, score, confirmations):
    return DailyEvidence(
        day=day,
        close=close,
        score=score,
        state="HIGH_RISK",
        available_weight=0.72,
        cash_signal=False,
        critical_confirmations=confirmations,
        coverage=1.0,
    )


def test_persistent_regime_is_one_event():
    evidence = [
        row("2026-01-01", 100, 40, 1),
        row("2026-01-02", 99, 60, 3),
        row("2026-01-03", 98, 62, 3),
        row("2026-01-04", 97, 64, 4),
        row("2026-01-05", 98, 40, 1),
        row("2026-01-06", 97, 66, 3),
    ]
    assert signal_event_indices(evidence, score_threshold=56, confirmations=3) == [1, 5]


def test_persistence_delays_event_until_confirmed():
    evidence = [
        row("2026-01-01", 100, 60, 3),
        row("2026-01-02", 99, 61, 3),
        row("2026-01-03", 98, 62, 3),
    ]
    assert signal_event_indices(evidence, score_threshold=56, confirmations=3, persistence=2) == [1]
    assert signal_event_indices(evidence, score_threshold=56, confirmations=3, persistence=3) == [2]


def test_false_event_uses_forward_only_window():
    evidence = [row(f"2026-01-{i:02d}", 100 - (i - 1), 60 if i == 1 else 20, 3 if i == 1 else 0) for i in range(1, 22)]
    events = signal_event_indices(evidence, score_threshold=56, confirmations=3)
    evaluated, false, rate = false_event_stats(evidence, events, horizon_rows=20, drawdown_threshold_pct=-8)
    assert evaluated == 1
    assert false == 0
    assert rate == 0.0
