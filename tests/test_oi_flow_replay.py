from moex_crash_radar.oi_flow_alignment import AlignedFutoi
from moex_crash_radar.oi_flow_replay import ReplayBar, build_replay_rows


def _bar(ts: str) -> ReplayBar:
    return ReplayBar(ts, 100.0, 102.0, 99.0, 101.0, 1000.0)


def _futoi(decision: str, available: str) -> AlignedFutoi:
    return AlignedFutoi(
        decision_timestamp=decision,
        source_moment=decision,
        source_available_at=available,
        ticker="Si",
        total_oi=1000,
        retail_net=-100,
        legal_net=100,
        delta_total_oi=10,
        delta_retail_net=-5,
        delta_legal_net=5,
    )


def test_replay_ready_when_coverage_is_complete_and_safe():
    bars = [_bar("2026-08-03T10:00:00"), _bar("2026-08-03T11:00:00")]
    futoi = [
        _futoi("2026-08-03T10:00:00", "2026-08-03T09:59:59"),
        _futoi("2026-08-03T11:00:00", "2026-08-03T10:59:59"),
    ]
    rows, coverage = build_replay_rows(bars, futoi)
    assert len(rows) == 2
    assert coverage.status == "READY"
    assert coverage.coverage_pct == 100.0
    assert coverage.point_in_time_violations == 0


def test_replay_fails_on_lookahead_publication():
    bars = [_bar("2026-08-03T10:00:00")]
    futoi = [_futoi("2026-08-03T10:00:00", "2026-08-03T10:00:01")]
    rows, coverage = build_replay_rows(bars, futoi)
    assert rows == []
    assert coverage.status == "FAIL"
    assert coverage.point_in_time_violations == 1


def test_replay_fails_when_coverage_below_90_percent():
    bars = [_bar(f"2026-08-03T{hour:02d}:00:00") for hour in range(10, 20)]
    futoi = [
        _futoi(f"2026-08-03T{hour:02d}:00:00", f"2026-08-03T{hour-1:02d}:59:59")
        for hour in range(10, 18)
    ]
    rows, coverage = build_replay_rows(bars, futoi)
    assert len(rows) == 8
    assert coverage.coverage_pct == 80.0
    assert coverage.status == "FAIL"
