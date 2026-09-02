from moex_crash_radar.bubble_history import HistoricalBubblePoint
from moex_crash_radar.bubble_validation import BubbleEpisode, validate_bubble
from moex_crash_radar.history import DailyEvidence


def _e(day, close):
    return DailyEvidence(day, close, 40, "CAUTION", .72, False, 1, 1.0)


def _p(day, score):
    return HistoricalBubblePoint(day, score, "BUBBLE_BUILD_UP", 0, 1, "STABLE", .60)


def test_validation_fails_closed_on_low_coverage():
    evidence = [_e(f"2026-01-{i:02d}", 100) for i in range(1, 11)]
    points = [_p(row.day, 65) if i < 5 else _p(row.day, None) for i, row in enumerate(evidence)]
    result = validate_bubble(evidence, points, [])
    assert result.status == "DATA_GATE_FAIL_NO_DECISION"


def test_validation_requires_episode_detection_and_advance():
    days = [f"2026-01-{i:02d}" for i in range(1, 21)]
    closes = [100,101,102,103,104,105,104,103,102,100,98,96,94,92,90,89,90,91,92,93]
    evidence = [_e(d, c) for d, c in zip(days, closes)]
    points = [_p(d, 65 if 5 <= i <= 10 else 40) for i, d in enumerate(days)]
    episode = BubbleEpisode("TEST", "2026-01-01", "2026-01-16")
    result = validate_bubble(evidence, points, [episode], forward_rows=15, exit_event_days=["2026-01-10"])
    assert result.detected_episodes == 1
    assert result.median_advance_vs_exit_days is not None
    assert result.median_advance_vs_exit_days >= 0
