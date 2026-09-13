from scripts.btc_entry_radar_journal_r1_4_5 import confirm_state


def test_no_trade_is_immediate():
    confirmed, count, pending = confirm_state(
        "NO_TRADE", [{"state": "LONG_READY"}], "LONG_READY"
    )
    assert confirmed == "NO_TRADE"
    assert count == 1
    assert pending is False


def test_first_positive_snapshot_is_pending():
    confirmed, count, pending = confirm_state(
        "ARMED", [{"state": "NO_TRADE"}], "NO_TRADE"
    )
    assert confirmed == "NO_TRADE"
    assert count == 1
    assert pending is True


def test_second_identical_positive_snapshot_confirms():
    confirmed, count, pending = confirm_state(
        "ARMED", [{"state": "NO_TRADE"}, {"state": "ARMED"}], "NO_TRADE"
    )
    assert confirmed == "ARMED"
    assert count == 2
    assert pending is False


def test_different_positive_state_restarts_confirmation():
    confirmed, count, pending = confirm_state(
        "LONG_READY", [{"state": "ARMED"}], "ARMED"
    )
    assert confirmed == "ARMED"
    assert count == 1
    assert pending is True
