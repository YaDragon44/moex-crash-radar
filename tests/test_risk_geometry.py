from datetime import datetime, timedelta

from moex_crash_radar.moex import Candle
from moex_crash_radar.public_baseline import BaselineConfig
from moex_crash_radar.risk_geometry import GEOMETRIES, compare_geometries, run_geometry
from moex_crash_radar.roll_chain import RollBar


def _bars(n=500):
    out = []
    t = datetime(2026, 1, 5, 10)
    price = 100.0
    for i in range(n):
        drift = 0.40 if (i // 80) % 2 == 0 else -0.35
        shock = -0.8 if i % 11 == 0 else (0.65 if i % 17 == 0 else 0.0)
        o = price
        c = price + drift + shock
        h = max(o, c) + 0.35
        l = min(o, c) - 0.35
        candle = Candle(begin=t.isoformat(sep=" "), open=o, close=c, high=h, low=l, value=None, volume=1000 + (600 if i % 9 == 0 else 0))
        secid = "MXH6" if i < n // 2 else "MXM6"
        out.append(RollBar(candle=candle, secid=secid, family="MX", expiry="2026-03-19" if i < n // 2 else "2026-06-18"))
        price = c
        t += timedelta(hours=1)
    return out


def test_geometry_catalog_is_small_and_explicit():
    assert GEOMETRIES == ("CONTROL", "ATR_INVALIDATION", "HTF_LIQUIDITY", "TIME_INVALIDATION")


def test_compare_geometries_returns_all_models_and_variants():
    rows = compare_geometries(_bars(), config=BaselineConfig(rvol_sessions=3))
    assert len(rows) == 12
    assert {(r.model, r.geometry) for r in rows} == {(m, g) for m in ("M0", "M1", "M5") for g in GEOMETRIES}


def test_candidate_preservation_is_bounded():
    for geometry in GEOMETRIES:
        r = run_geometry(_bars(), "M0", geometry, BaselineConfig(rvol_sessions=3))
        assert 0 <= r.accepted <= r.candidates
        assert 0.0 <= r.preservation_pct <= 100.0


def test_roll_boundary_does_not_create_cross_contract_trade():
    bars = _bars(240)
    first = run_geometry(bars[:120], "M0", "TIME_INVALIDATION", BaselineConfig(rvol_sessions=3))
    second = run_geometry(bars[120:], "M0", "TIME_INVALIDATION", BaselineConfig(rvol_sessions=3))
    combined = run_geometry(bars, "M0", "TIME_INVALIDATION", BaselineConfig(rvol_sessions=3))
    assert combined.accepted == first.accepted + second.accepted
