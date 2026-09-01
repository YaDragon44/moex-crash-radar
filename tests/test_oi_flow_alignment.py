from __future__ import annotations

from moex_crash_radar.futoi import pair_snapshots, parse_futoi_rows
from moex_crash_radar.oi_flow_alignment import align_decision_times, latest_safe_pair


def _pairs():
    rows = [
        {"TICKER":"RI","CLGROUP":"FIZ","POS":50,"POS_LONG":120,"POS_SHORT":-70,"POS_LONG_NUM":10,"POS_SHORT_NUM":8,"SEQNUM":1,"MOMENT":"2026-07-01 10:54:00","SYSTIME":"2026-07-01 10:55:10"},
        {"TICKER":"RI","CLGROUP":"YUR","POS":-50,"POS_LONG":80,"POS_SHORT":-130,"POS_LONG_NUM":4,"POS_SHORT_NUM":6,"SEQNUM":1,"MOMENT":"2026-07-01 10:54:00","SYSTIME":"2026-07-01 10:55:11"},
        {"TICKER":"RI","CLGROUP":"FIZ","POS":80,"POS_LONG":160,"POS_SHORT":-80,"POS_LONG_NUM":11,"POS_SHORT_NUM":8,"SEQNUM":2,"MOMENT":"2026-07-01 11:54:00","SYSTIME":"2026-07-01 11:55:10"},
        {"TICKER":"RI","CLGROUP":"YUR","POS":-80,"POS_LONG":70,"POS_SHORT":-150,"POS_LONG_NUM":4,"POS_SHORT_NUM":7,"SEQNUM":2,"MOMENT":"2026-07-01 11:54:00","SYSTIME":"2026-07-01 11:55:12"},
    ]
    return pair_snapshots(parse_futoi_rows(rows))


def test_snapshot_published_after_hour_close_is_not_visible():
    pairs = _pairs()
    assert latest_safe_pair(pairs, ticker="RI", decision_timestamp="2026-07-01 10:55:10") is None
    safe = latest_safe_pair(pairs, ticker="RI", decision_timestamp="2026-07-01 10:55:11")
    assert safe is not None
    assert safe.moment == "2026-07-01 10:54:00"


def test_asof_alignment_uses_latest_published_pair_and_computes_deltas():
    aligned = align_decision_times(
        _pairs(),
        ticker="RI",
        decision_timestamps=["2026-07-01 11:00:00", "2026-07-01 12:00:00"],
    )
    assert len(aligned) == 2
    assert aligned[0].total_oi == 200
    assert aligned[0].delta_total_oi is None
    assert aligned[1].total_oi == 230
    assert aligned[1].delta_total_oi == 30
    assert aligned[1].delta_retail_net == 30
    assert aligned[1].delta_legal_net == -30
    assert aligned[1].source_available_at == "2026-07-01 11:55:12"


def test_no_future_snapshot_is_backfilled_into_earlier_decision():
    aligned = align_decision_times(
        _pairs(), ticker="RI", decision_timestamps=["2026-07-01 10:30:00"]
    )
    assert aligned == []
