from datetime import date

from moex_crash_radar.engine import DataQuality
from moex_crash_radar.oil_rub import (
    MarketSeries,
    brent_return_stress,
    calculate_oil_rub_signal,
    rub_return_stress,
    select_nearest_brent_future,
)


def test_select_nearest_active_brent_future():
    payload = {
        "securities": {
            "columns": ["SECID", "LASTTRADEDATE", "LASTDELDATE"],
            "data": [
                ["BR-8.26", "2026-08-03", "2026-08-03"],
                ["BR-9.26", "2026-09-01", "2026-09-01"],
                ["BR-10.26", "2026-10-01", "2026-10-01"],
                ["Si-9.26", "2026-09-17", "2026-09-17"],
            ],
        }
    }
    assert select_nearest_brent_future(payload, as_of=date(2026, 8, 28)) == "BR-9.26"


def test_oil_and_rub_stress_direction():
    assert brent_return_stress(-15) > brent_return_stress(8)
    assert rub_return_stress(15) > rub_return_stress(-8)


def _series(name: str, secid: str, start: float, step: float, last_day=date(2026, 8, 28)) -> MarketSeries:
    return MarketSeries(name, secid, tuple(start + i * step for i in range(30)), last_day)


def test_oil_rub_builds_live_signal_with_both_markets():
    result = calculate_oil_rub_signal(
        brent=_series("Brent", "BR-9.26", 85.0, -0.5),
        cnyrub=_series("CNYRUB", "CNYRUB_TOM", 11.0, 0.05),
        today=date(2026, 8, 28),
    )
    assert result.signal is not None
    assert result.signal.quality == DataQuality.LIVE
    assert result.component_coverage == 1.0
    assert result.brent_secid == "BR-9.26"
    assert result.brent_return_20d < 0
    assert result.cnyrub_return_20d > 0
    assert "not a probability" in result.note


def test_oil_rub_requires_both_assets():
    result = calculate_oil_rub_signal(
        brent=_series("Brent", "BR-9.26", 85.0, -0.5),
        cnyrub=None,
        today=date(2026, 8, 28),
    )
    assert result.signal is None
    assert "DATA_INSUFFICIENT" in result.note


def test_oil_rub_rejects_stale_market_data():
    result = calculate_oil_rub_signal(
        brent=_series("Brent", "BR-9.26", 85.0, -0.5, date(2026, 8, 20)),
        cnyrub=_series("CNYRUB", "CNYRUB_TOM", 11.0, 0.05, date(2026, 8, 20)),
        today=date(2026, 8, 28),
    )
    assert result.signal is None
