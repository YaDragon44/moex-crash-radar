from moex_crash_radar.futoi import coverage_ratio, is_point_in_time_safe, pair_snapshots, parse_futoi_rows


def rows():
    return [
        {"TICKER": "Si", "CLGROUP": "FIZ", "POS": 100, "POS_LONG": 180, "POS_SHORT": -80,
         "POS_LONG_NUM": 10, "POS_SHORT_NUM": 6, "SEQNUM": 1,
         "MOMENT": "2026-09-01T12:00:00", "SYSTIME": "2026-09-01T12:00:05"},
        {"TICKER": "Si", "CLGROUP": "YUR", "POS": -100, "POS_LONG": 20, "POS_SHORT": -120,
         "POS_LONG_NUM": 2, "POS_SHORT_NUM": 3, "SEQNUM": 1,
         "MOMENT": "2026-09-01T12:00:00", "SYSTIME": "2026-09-01T12:00:06"},
    ]


def test_futoi_signed_short_and_pair_total_oi():
    snapshots = parse_futoi_rows(rows())
    assert snapshots[0].net == 100
    assert snapshots[1].net == -100
    pairs = pair_snapshots(snapshots)
    assert len(pairs) == 1
    assert pairs[0].total_oi == 200


def test_pair_requires_both_client_groups():
    snapshots = parse_futoi_rows(rows()[:1])
    assert pair_snapshots(snapshots) == []


def test_coverage_counts_only_complete_pairs():
    pairs = pair_snapshots(parse_futoi_rows(rows()))
    assert coverage_ratio(["2026-09-01T12:00:00", "2026-09-01T13:00:00"], pairs) == 0.5


def test_point_in_time_rejects_future_publication():
    pair = pair_snapshots(parse_futoi_rows(rows()))[0]
    assert is_point_in_time_safe(pair, "2026-09-01T12:00:06") is True
    assert is_point_in_time_safe(pair, "2026-09-01T12:00:05") is False
