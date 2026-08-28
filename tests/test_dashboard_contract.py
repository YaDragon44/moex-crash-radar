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
    core["rate_ofz"] = {"score": 52.0, "quality": "LIVE"}
    return {
        "release": "R0.5.1 Rate / OFZ Live Integration",
        "as_of": "2026-08-28T09:45:00+03:00",
        "source": "MOEX ISS",
        "secid": "IMOEX",
        "last_close": 2087.96,
        "data_quality": "LIVE",
        "signals": core,
        "context": {
            "score": None,
            "state": "DATA_INSUFFICIENT",
            "quality": "N/A",
            "coverage": 0.35,
            "available_groups": 1,
            "total_groups": 4,
            "groups": {
                "rate_ofz": {
                    "score": 52.0,
                    "quality": "LIVE",
                    "key_rate": 14.0,
                    "key_rate_day": "2026-08-27",
                    "median_long_ofz_yield": 14.8,
                    "ofz_count": 18,
                    "rgbi_return_5d": -0.5,
                    "rgbi_return_20d": -1.2,
                    "component_coverage": 1.0,
                    "sources": ["Bank of Russia", "MOEX ISS TQOB", "MOEX ISS RGBI"],
                },
                "oil_rub": {"score": None, "quality": "N/A"},
                "macro_earnings": {"score": None, "quality": "N/A"},
                "news_geopolitics": {"score": None, "quality": "N/A"},
            },
        },
        "crash": {"score": 55.94, "available_weight": 0.72, "critical_confirmations": 1},
        "crash_history": [
            {"day": "2026-08-27", "score": 53.0, "state": "DEFENSIVE"},
            {"day": "2026-08-28", "score": 55.94, "state": "DEFENSIVE"},
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


def test_sourced_rate_ofz_requires_official_sources():
    s = good_snapshot(); s["context"]["groups"]["rate_ofz"]["sources"] = ["unknown"]
    assert any("official CBR and MOEX" in e for e in validate_dashboard_snapshot(s))


def test_sourced_rate_ofz_requires_component_coverage():
    s = good_snapshot(); s["context"]["groups"]["rate_ofz"]["component_coverage"] = 0.4
    assert any("component_coverage" in e for e in validate_dashboard_snapshot(s))


def test_rate_ofz_display_signal_must_match_context_group():
    s = good_snapshot(); s["signals"]["rate_ofz"]["score"] = 99
    assert any("must match" in e for e in validate_dashboard_snapshot(s))


def test_one_rate_ofz_group_cannot_unlock_aggregate_context():
    s = good_snapshot(); s["context"]["score"] = 52.0; s["context"]["state"] = "NEUTRAL"
    assert any("one context group" in e for e in validate_dashboard_snapshot(s))


def test_unsourced_context_groups_cannot_be_fabricated():
    s = good_snapshot(); s["context"]["groups"]["oil_rub"] = {"score": 42, "quality": "LIVE"}
    assert any("oil_rub" in e for e in validate_dashboard_snapshot(s))


def test_context_without_score_must_be_data_insufficient():
    s = good_snapshot(); s["context"]["state"] = "NEUTRAL"
    assert any("DATA_INSUFFICIENT" in e for e in validate_dashboard_snapshot(s))


def test_cash_stage_requires_boolean_confirmation():
    s = good_snapshot(); s["exit_gate"]["stage"] = "CASH_CONFIRMED"
    assert any("cash_confirmed=true" in e for e in validate_dashboard_snapshot(s))


def test_synthetic_marker_is_rejected():
    s = good_snapshot(); s["note"] = "synthetic fallback"
    assert any("synthetic" in e for e in validate_dashboard_snapshot(s))


def test_crash_history_is_required():
    s = good_snapshot(); del s["crash_history"]
    assert any("crash_history" in e for e in validate_dashboard_snapshot(s))


def test_dashboard_html_has_release_and_review_hooks():
    html = open("web/r044.html", encoding="utf-8").read()
    for token in (
        "market_snapshot.json", "R0.5.1", "MARKET", "ТОЛПА", "РИСК", "РЕЖИМ",
        "ПЕРЕХОД", "ДЕЙСТВИЕ", "9 КЛЮЧЕВЫХ ИНДИКАТОРОВ", "ВЫВОД:",
        "РЕКОМЕНДАЦИЯ:", "ИНВЕСТОР", "ТРЕЙДЕР", "КРИЗИСЫ", "Начало СВО",
        "COVID", "crash_history", "data_quality==='LIVE'", "DELAYED", "contextState",
        "КС ${r.key_rate", "OFZ ${Number(r.median_long_ofz_yield)", "RGBI20",
    ):
        assert token in html
    assert "@media(max-width:1200px)" in html
    assert "@media(max-width:700px)" in html


def test_dashboard_does_not_turn_crowd_na_into_fake_score():
    html = open("web/r044.html", encoding="utf-8").read()
    assert "Crowd Engine ещё не подключён" in html
    assert "crowdState').textContent='N/A" in html


def test_delayed_quality_downgrades_new_actions():
    html = open("web/r044.html", encoding="utf-8").read()
    assert "WAIT ДО LIVE-ПОДТВЕРЖДЕНИЯ" in html
    assert "СОХРАНЯТЬ СНИЖЕННЫЙ РИСК" in html


def test_rate_ofz_context_cannot_directly_change_calibrated_exit_action():
    html = open("web/r044.html", encoding="utf-8").read()
    assert "Контекст пока не меняет calibrated EXIT Gate" in html
    assert "не трактовать Context как самостоятельный CASH-сигнал" in html
