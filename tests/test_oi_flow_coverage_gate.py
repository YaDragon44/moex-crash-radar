from moex_crash_radar.futoi import pair_snapshots, parse_futoi_rows
from moex_crash_radar.oi_flow_coverage_gate import evaluate_coverage_gate, full_model_gate


def _pairs(ticker="RI"):
    rows = []
    for h in (10, 11, 12):
        moment = f"2026-07-01 {h}:54:00"
        systime = f"2026-07-01 {h}:55:00"
        rows += [
            {"TICKER":ticker,"CLGROUP":"FIZ","POS":50,"POS_LONG":120+h,"POS_SHORT":-70,"POS_LONG_NUM":10,"POS_SHORT_NUM":8,"SEQNUM":h,"MOMENT":moment,"SYSTIME":systime},
            {"TICKER":ticker,"CLGROUP":"YUR","POS":-50,"POS_LONG":80,"POS_SHORT":-(130+h),"POS_LONG_NUM":4,"POS_SHORT_NUM":6,"SEQNUM":h,"MOMENT":moment,"SYSTIME":systime},
        ]
    return pair_snapshots(parse_futoi_rows(rows))


def test_ready_when_hourly_alignment_and_lag_pass():
    result = evaluate_coverage_gate(
        ticker="RI",
        pairs=_pairs(),
        decision_timestamps=[
            "2026-07-01 11:00:00",
            "2026-07-01 12:00:00",
            "2026-07-01 13:00:00",
        ],
        min_alignment_coverage_pct=95.0,
        max_median_publication_lag_sec=120,
    )
    assert result.status == "READY"
    assert result.alignment_coverage_pct == 100.0
    assert result.median_publication_lag_sec == 60.0


def test_fail_when_hourly_coverage_is_low():
    result = evaluate_coverage_gate(
        ticker="RI",
        pairs=_pairs(),
        decision_timestamps=[
            "2026-07-01 09:00:00",
            "2026-07-01 10:00:00",
            "2026-07-01 11:00:00",
            "2026-07-01 12:00:00",
            "2026-07-01 13:00:00",
        ],
        min_alignment_coverage_pct=80.0,
    )
    assert result.status == "FAIL"
    assert result.alignment_coverage_pct == 60.0


def test_fail_when_publication_lag_is_excessive():
    result = evaluate_coverage_gate(
        ticker="RI",
        pairs=_pairs(),
        decision_timestamps=["2026-07-01 11:00:00", "2026-07-01 12:00:00"],
        max_median_publication_lag_sec=30,
    )
    assert result.status == "FAIL"


def test_full_model_gate_requires_every_requested_ticker_ready():
    ready = evaluate_coverage_gate(
        ticker="RI", pairs=_pairs(), decision_timestamps=["2026-07-01 11:00:00"]
    )
    missing = evaluate_coverage_gate(
        ticker="SI", pairs=[], decision_timestamps=["2026-07-01 11:00:00"]
    )
    gate = full_model_gate([ready, missing])
    assert gate["status"] == "NO-GO"
    assert gate["blocked_tickers"] == ["SI"]
