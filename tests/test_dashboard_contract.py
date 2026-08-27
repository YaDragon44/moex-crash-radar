from moex_crash_radar.dashboard_contract import validate_dashboard_snapshot


def good_snapshot():
    core = {
        key: {"score": 50.0, "quality": "LIVE"}
        for key in (
            "market_structure",
            "breadth",
            "volume_distribution",
            "volatility_liquidity",
            "levels_momentum",
        )
    }
    return {
        "release": "R0.4.3 Analytical UX Completion",
        "as_of": "2026-08-27T17:00:00+03:00",
        "source": "MOEX ISS",
        "secid": "IMOEX",
        "last_close": 2087.96,
        "data_quality": "LIVE",
        "signals": core,
        "crash": {"score": 55.94, "available_weight": 0.72, "critical_confirmations": 1},
        "crash_history": [
            {"day": "2026-08-26", "score": 53.0, "state": "DEFENSIVE"},
            {"day": "2026-08-27", "score": 55.94, "state": "DEFENSIVE"},
        ],
        "exit_gate": {
            "stage": "EARLY_WARNING",
            "cash_confirmed": False,
            "params": {
                "score_threshold": 65.0,
                "early_warning_threshold": 56.0,
                "confirmations": 3,
                "persistence": 2,
                "max_5d_return_pct": -3.0,
                "cooldown_rows": 30,
                "require_breadth_volume": False,
                "rearm_clear_rows": 3,
            },
        },
        "bottom": {"score": None, "state": "DATA_INSUFFICIENT", "buy_back_signal": False},
        "calibration": {
            "release": "R0.3.3",
            "false_event_rate": 0.2857,
            "detected_episodes": "4/4",
            "median_lead_days": 28.5,
            "total_exit_events": 14,
            "false_exit_events": 4,
        },
        "note": "Live MOEX market layer is active.",
    }


def test_valid_dashboard_contract_passes():
    assert validate_dashboard_snapshot(good_snapshot()) == []


def test_missing_core_signal_fails():
    s = good_snapshot(); del s["signals"]["breadth"]
    assert any("breadth" in e for e in validate_dashboard_snapshot(s))


def test_optional_unsourced_signal_cannot_be_fabricated():
    s = good_snapshot(); s["signals"]["rate_ofz"] = {"score": 42, "quality": "LIVE"}
    assert any("rate_ofz" in e for e in validate_dashboard_snapshot(s))


def test_cash_stage_requires_boolean_confirmation():
    s = good_snapshot(); s["exit_gate"]["stage"] = "CASH_CONFIRMED"
    assert any("cash_confirmed=true" in e for e in validate_dashboard_snapshot(s))


def test_synthetic_marker_is_rejected():
    s = good_snapshot(); s["note"] = "synthetic fallback"
    assert any("synthetic" in e for e in validate_dashboard_snapshot(s))


def test_crash_history_is_required():
    s = good_snapshot(); del s["crash_history"]
    assert any("crash_history" in e for e in validate_dashboard_snapshot(s))


def test_dashboard_html_has_r043_analytical_ux_hooks():
    html = open("web/index.html", encoding="utf-8").read()
    for token in (
        "market_snapshot.json", "CASH CONFIRMED", "falseRate", "episodes", "lead",
        "rate_ofz", "news_geopolitics", "ВЫВОДЫ", "ГИПОТЕЗЫ", "РЕКОМЕНДАЦИИ",
        "investorAction", "traderAction", "whyInvestor", "whyTrader", "crash_history", "R0.4.3",
    ):
        assert token in html
    assert "@media(max-width:1200px)" in html
    assert "@media(max-width:700px)" in html
