from scripts.run_r1_5_3b_transition_replay import flags, outcome
from moex_crash_radar.history import DailyEvidence


def row(day, close=100, coverage=.8, ms=20, br=45, vol=45, vl=55):
    return DailyEvidence(day, close, 0, "LOW", 1, False, 0, coverage, ms, br, vol, vl)


def test_locked_m4_definition_and_coverage_fail_closed():
    rows=[row(f"2024-01-{i+1:02d}", close=100+i) for i in range(6)]
    assert flags(rows,5)["M4"] is True
    rows[-1]=row("2024-01-06",105,coverage=.69)
    assert flags(rows,5) is None


def test_locked_20_session_outcome():
    rows=[row(f"2024-01-{i+1:02d}" if i<31 else f"2024-02-{i-30:02d}", close=100) for i in range(25)]
    rows[10]=row("2024-01-11",91)
    assert outcome(rows,0) is True
