from __future__ import annotations

from datetime import datetime, timezone

from moex_crash_radar.oi_flow_audit import _extract_rows, public_safe_end
from moex_crash_radar.futoi import pair_snapshots, parse_futoi_rows, is_point_in_time_safe


def _payload():
    columns = [
        "SESS_ID", "TICKER", "CLGROUP", "POS", "POS_LONG", "POS_SHORT",
        "POS_LONG_NUM", "POS_SHORT_NUM", "SEQNUM", "MOMENT", "SYSTIME",
    ]
    return {
        "futoi": {
            "columns": columns,
            "data": [
                [1, "RI", "FIZ", 50, 120, -70, 10, 8, 1, "2026-07-01 10:04:00", "2026-07-01 10:05:10"],
                [1, "RI", "YUR", -50, 80, -130, 4, 6, 1, "2026-07-01 10:04:00", "2026-07-01 10:05:11"],
            ],
        }
    }


def test_extract_rows_detects_futoi_block_by_columns():
    rows = _extract_rows(_payload())
    assert len(rows) == 2
    assert rows[0]["TICKER"] == "RI"


def test_pairing_and_total_oi_use_gross_long_side():
    pairs = pair_snapshots(parse_futoi_rows(_extract_rows(_payload())))
    assert len(pairs) == 1
    assert pairs[0].total_oi == 200
    assert pairs[0].retail.net == 50
    assert pairs[0].legal.net == -50


def test_systime_is_the_availability_gate():
    pair = pair_snapshots(parse_futoi_rows(_extract_rows(_payload())))[0]
    assert not is_point_in_time_safe(pair, "2026-07-01 10:05:10")
    assert is_point_in_time_safe(pair, "2026-07-01 10:05:11")


def test_public_safe_end_respects_15_day_delay():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    assert public_safe_end(now) == "2026-08-17"
