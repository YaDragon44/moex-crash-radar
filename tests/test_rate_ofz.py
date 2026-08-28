from datetime import date

from moex_crash_radar.engine import DataQuality
from moex_crash_radar.rate_ofz import (
    KeyRatePoint,
    OfzMarketPoint,
    calculate_rate_ofz_signal,
    key_rate_stress,
    ofz_yield_stress,
    parse_cbr_key_rate_html,
    parse_ofz_market,
    rgbi_return_stress,
)


def test_parse_cbr_key_rate_html():
    html = "<table><tr><td>27.08.2026</td><td>14,00</td></tr><tr><td>26.08.2026</td><td>14.00</td></tr></table>"
    points = parse_cbr_key_rate_html(html)
    assert len(points) == 2
    assert points[-1].day == date(2026, 8, 27)
    assert points[-1].rate == 14.0


def test_parse_ofz_market_filters_for_long_maturity_and_valid_yield():
    payload = {
        "securities": {
            "columns": ["SECID", "MATDATE"],
            "data": [["SU26254RMFS3", "2040-10-03"], ["SHORT", "2027-01-01"]],
        },
        "marketdata": {
            "columns": ["SECID", "YIELD", "VALTODAY"],
            "data": [["SU26254RMFS3", 14.7, 1000000], ["SHORT", 12.0, 1000]],
        },
    }
    rows = parse_ofz_market(payload, as_of=date(2026, 8, 28))
    assert [x.secid for x in rows] == ["SU26254RMFS3"]
    assert rows[0].yield_pct == 14.7


def test_component_stress_is_monotonic():
    assert key_rate_stress(18) > key_rate_stress(10)
    assert ofz_yield_stress(18) > ofz_yield_stress(10)
    assert rgbi_return_stress(-6) > rgbi_return_stress(3)


def _ofz(n=6, y=15.0):
    return [
        OfzMarketPoint(f"OFZ{i}", date(2040, 1, 1), y + i * 0.1, 1_000_000)
        for i in range(n)
    ]


def test_rate_ofz_requires_fresh_key_rate():
    result = calculate_rate_ofz_signal(
        key_rate=KeyRatePoint(date(2026, 8, 1), 14.0),
        long_ofz=_ofz(),
        rgbi_closes=[100 + i * 0.1 for i in range(30)],
        today=date(2026, 8, 28),
    )
    assert result.signal is None
    assert "DATA_INSUFFICIENT" in result.note


def test_rate_ofz_builds_explainable_live_signal():
    result = calculate_rate_ofz_signal(
        key_rate=KeyRatePoint(date(2026, 8, 27), 14.0),
        long_ofz=_ofz(),
        rgbi_closes=[110 - i * 0.5 for i in range(30)],
        today=date(2026, 8, 28),
    )
    assert result.signal is not None
    assert result.signal.quality == DataQuality.LIVE
    assert 0 <= result.signal.score <= 100
    assert result.component_coverage == 1.0
    assert result.ofz_count == 6
    assert result.median_long_ofz_yield is not None
    assert "not a probability" in result.note


def test_rate_ofz_needs_enough_ofz_names_for_yield_component():
    result = calculate_rate_ofz_signal(
        key_rate=KeyRatePoint(date(2026, 8, 27), 14.0),
        long_ofz=_ofz(n=2),
        rgbi_closes=[],
        today=date(2026, 8, 28),
    )
    assert result.signal is None
    assert result.component_coverage == 0.35
