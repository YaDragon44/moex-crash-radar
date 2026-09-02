from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import requests

BTC_FGI_URL = "https://raw.githubusercontent.com/MetalGrey/btc-fgi-daily-2020/main/datasets/btc_with_fgi_4h.csv"
OI_URLS = {
    "bybit": "https://gist.githubusercontent.com/vadim-isakov/bb200237e444cf6656535c22840f45fd/raw/btcusdt_open_interest_4h.csv",
    "binance": "https://gist.githubusercontent.com/vadim-isakov/59a8df24e2cb609bbc789b9e43f75c79/raw/btcusdt_open_interest_4h.csv",
}

FEE_PER_SIDE = 0.001
DEV_END = pd.Timestamp("2023-12-31 23:59:59")
OOS_START = pd.Timestamp("2024-01-01 00:00:00")
OI_WINDOW = 6 * 90  # 90 days on 4H bars
OI_STABILIZATION_LOOKBACK = 3
PRICE_CONFIRM_BARS = 3
SWING_LOOKBACK = 6


def fetch_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    from io import StringIO
    return pd.read_csv(StringIO(r.text))


def load_btc_fgi() -> pd.DataFrame:
    df = fetch_csv(BTC_FGI_URL)
    rename = {
        "Fear & Greed Index": "fgi",
        "Fear & Greed Classification": "fgi_class",
    }
    df = df.rename(columns=rename)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)
    df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    for c in ["open", "high", "low", "close", "fgi"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Conservative anti-lookahead treatment: daily FGI for date D becomes usable only on D+1.
    df["date"] = df["timestamp"].dt.floor("D")
    daily = df.groupby("date", as_index=True)["fgi"].first().sort_index()
    safe_daily = daily.shift(1)
    df["fgi_safe"] = df["date"].map(safe_daily)
    prev_safe_daily = safe_daily.shift(1)
    df["fgi_prev_safe"] = df["date"].map(prev_safe_daily)
    df["fgi_reversal"] = df["fgi_safe"] > df["fgi_prev_safe"]

    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14, min_periods=14).mean()
    df["prev3_high"] = df["high"].shift(1).rolling(PRICE_CONFIRM_BARS).max()
    df["price_confirm"] = df["close"] > df["prev3_high"]
    df["prev_swing_low"] = df["low"].shift(1).rolling(SWING_LOOKBACK).min()
    return df


def load_oi(exchange: str) -> Tuple[pd.DataFrame, Dict]:
    raw = fetch_csv(OI_URLS[exchange])
    raw = raw.rename(columns={raw.columns[0]: "timestamp", raw.columns[1]: "oi"})
    ts = raw["timestamp"]
    if pd.api.types.is_numeric_dtype(ts) or ts.astype(str).str.fullmatch(r"\d+").all():
        raw["timestamp"] = pd.to_datetime(pd.to_numeric(ts), unit="ms", errors="coerce")
    else:
        raw["timestamp"] = pd.to_datetime(ts, errors="coerce")
    raw["oi"] = pd.to_numeric(raw["oi"], errors="coerce")
    raw = raw.dropna(subset=["timestamp", "oi"]).sort_values("timestamp").drop_duplicates("timestamp")

    raw["gap_hours"] = raw["timestamp"].diff().dt.total_seconds().div(3600)
    raw["oi_ret4h"] = raw["oi"].pct_change()
    anomaly = (raw["gap_hours"].notna() & (raw["gap_hours"] != 4)) | (raw["oi_ret4h"].abs() > 0.50)
    raw["quality_ok"] = ~anomaly
    # Invalid rows are excluded from signal construction, not silently interpolated.
    raw.loc[~raw["quality_ok"], "oi"] = np.nan

    audit = {
        "rows": int(len(raw)),
        "first_timestamp": str(raw["timestamp"].min()),
        "last_timestamp": str(raw["timestamp"].max()),
        "gap_or_anomaly_rows": int((~raw["quality_ok"]).sum()),
        "quality_coverage_pct": round(float(raw["quality_ok"].mean() * 100), 3),
    }
    return raw[["timestamp", "oi", "quality_ok"]], audit


def prepare_common(btc: pd.DataFrame, oi: pd.DataFrame, q: float) -> pd.DataFrame:
    df = btc.merge(oi, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
    df["oi_ret24"] = df["oi"].pct_change(6)
    df["oi_q"] = df["oi_ret24"].rolling(OI_WINDOW, min_periods=OI_WINDOW).quantile(q)
    df["deleveraging"] = df["oi_ret24"] <= df["oi_q"]
    df["recent_deleveraging"] = (
        df["deleveraging"].shift(1).rolling(OI_STABILIZATION_LOOKBACK, min_periods=1).max().fillna(0).astype(bool)
    )
    df["oi_stabilized"] = df["recent_deleveraging"] & (~df["deleveraging"])
    # Fair comparison starts only once the OI percentile is available.
    df = df[df["oi_q"].notna()].copy().reset_index(drop=True)
    return df


def signal_for(df: pd.DataFrame, model: str) -> pd.Series:
    price = df["price_confirm"].fillna(False)
    if model == "M1A":
        return (df["fgi_safe"] <= 25) & price
    if model == "M1B":
        return (df["fgi_safe"] <= 35) & df["fgi_reversal"].fillna(False) & price
    if model == "M2":
        return (
            (df["fgi_safe"] <= 35)
            & df["fgi_reversal"].fillna(False)
            & df["oi_stabilized"].fillna(False)
            & price
        )
    raise ValueError(model)


def run_long_only(df: pd.DataFrame, entry_signal: pd.Series) -> Tuple[pd.Series, pd.DataFrame]:
    equity = 1.0
    position = False
    entry_price = np.nan
    initial_stop = np.nan
    eq = []
    trades = []

    for i, row in df.iterrows():
        close = float(row["close"])
        if position and i > 0:
            prev_close = float(df.iloc[i - 1]["close"])
            equity *= close / prev_close

        exit_reason = None
        if position:
            fgi_exit = bool(
                pd.notna(row["fgi_safe"])
                and row["fgi_safe"] >= 70
                and pd.notna(row["fgi_prev_safe"])
                and row["fgi_safe"] < row["fgi_prev_safe"]
            )
            swing_exit = pd.notna(row["prev_swing_low"]) and close < float(row["prev_swing_low"])
            stop_exit = pd.notna(initial_stop) and close < float(initial_stop)
            if stop_exit:
                exit_reason = "initial_stop"
            elif swing_exit:
                exit_reason = "swing_failure"
            elif fgi_exit:
                exit_reason = "euphoria_reversal"

        if position and exit_reason:
            equity *= (1.0 - FEE_PER_SIDE)
            ret = close / entry_price - 1.0 - 2 * FEE_PER_SIDE
            trades[-1].update({
                "exit_time": str(row["timestamp"]),
                "exit_price": close,
                "return": ret,
                "exit_reason": exit_reason,
            })
            position = False
            entry_price = np.nan
            initial_stop = np.nan

        if (not position) and bool(entry_signal.iloc[i]):
            atr = row["atr14"]
            swing_low = row["prev_swing_low"]
            if pd.notna(atr) and pd.notna(swing_low) and atr > 0:
                candidate_stop = float(swing_low) - 0.5 * float(atr)
                stop_distance = close - candidate_stop
                if 0 < stop_distance <= 2.0 * float(atr):
                    equity *= (1.0 - FEE_PER_SIDE)
                    position = True
                    entry_price = close
                    initial_stop = candidate_stop
                    trades.append({
                        "entry_time": str(row["timestamp"]),
                        "entry_price": close,
                        "initial_stop": candidate_stop,
                    })

        eq.append(equity)

    if position:
        close = float(df.iloc[-1]["close"])
        equity *= (1.0 - FEE_PER_SIDE)
        eq[-1] = equity
        ret = close / entry_price - 1.0 - 2 * FEE_PER_SIDE
        trades[-1].update({
            "exit_time": str(df.iloc[-1]["timestamp"]),
            "exit_price": close,
            "return": ret,
            "exit_reason": "end_of_sample",
        })

    return pd.Series(eq, index=df.index, dtype=float), pd.DataFrame(trades)


def run_buy_hold(df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
    px = df["close"].astype(float)
    eq = px / px.iloc[0]
    eq *= (1.0 - FEE_PER_SIDE)
    eq.iloc[-1] *= (1.0 - FEE_PER_SIDE)
    trade = pd.DataFrame([{
        "entry_time": str(df.iloc[0]["timestamp"]),
        "entry_price": float(px.iloc[0]),
        "exit_time": str(df.iloc[-1]["timestamp"]),
        "exit_price": float(px.iloc[-1]),
        "return": float(px.iloc[-1] / px.iloc[0] - 1 - 2 * FEE_PER_SIDE),
        "exit_reason": "end_of_sample",
    }])
    return eq.reset_index(drop=True), trade


def metrics(df: pd.DataFrame, equity: pd.Series, trades: pd.DataFrame) -> Dict:
    if len(df) < 2:
        return {}
    years = max((df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds() / (365.25 * 86400), 1 / 365.25)
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)
    peak = equity.cummax()
    dd = equity / peak - 1
    maxdd = float(dd.min())
    r = equity.pct_change().fillna(0)
    sharpe = float((r.mean() / r.std(ddof=0)) * math.sqrt(6 * 365)) if r.std(ddof=0) > 0 else 0.0
    closed = trades[trades["return"].notna()].copy() if not trades.empty and "return" in trades.columns else pd.DataFrame()
    wins = closed[closed["return"] > 0]["return"] if not closed.empty else pd.Series(dtype=float)
    losses = closed[closed["return"] < 0]["return"] if not closed.empty else pd.Series(dtype=float)
    pf = float(wins.sum() / abs(losses.sum())) if len(losses) and abs(losses.sum()) > 0 else (float("inf") if len(wins) else 0.0)
    win_rate = float((closed["return"] > 0).mean()) if len(closed) else 0.0
    expectancy = float(closed["return"].mean()) if len(closed) else 0.0
    exposure = float((r != 0).mean())
    return {
        "start": str(df["timestamp"].iloc[0]),
        "end": str(df["timestamp"].iloc[-1]),
        "bars": int(len(df)),
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": maxdd,
        "sharpe": sharpe,
        "profit_factor": pf,
        "win_rate": win_rate,
        "expectancy": expectancy,
        "trades": int(len(closed)),
        "time_in_market": exposure,
        "return_over_maxdd": float(total_return / abs(maxdd)) if maxdd < 0 else float("inf"),
    }


def evaluate_slice(df: pd.DataFrame, model: str) -> Dict:
    if len(df) < 50:
        return {}
    if model == "M0":
        eq, tr = run_buy_hold(df)
    else:
        eq, tr = run_long_only(df, signal_for(df, model))
    return metrics(df.reset_index(drop=True), eq.reset_index(drop=True), tr)


def compare_edge(m1b: Dict, m2: Dict) -> Dict:
    if not m1b or not m2:
        return {"improved_count": 0, "tests": {}}
    tests = {
        "profit_factor": m2["profit_factor"] > m1b["profit_factor"],
        "expectancy": m2["expectancy"] > m1b["expectancy"],
        "max_drawdown": m2["max_drawdown"] > m1b["max_drawdown"],  # less negative is better
        "return_over_maxdd": m2["return_over_maxdd"] > m1b["return_over_maxdd"],
        "sharpe": m2["sharpe"] > m1b["sharpe"],
    }
    return {"improved_count": int(sum(tests.values())), "tests": tests}


def finite_json(obj):
    if isinstance(obj, dict):
        return {k: finite_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [finite_json(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def main() -> None:
    out = Path("artifacts")
    out.mkdir(exist_ok=True)
    btc = load_btc_fgi()
    report = {
        "release": "R1.3.2",
        "method": {
            "anti_lookahead": "FGI shifted by one full calendar day",
            "fee_per_side": FEE_PER_SIDE,
            "oi_percentile_window_bars": OI_WINDOW,
            "oi_percentiles_tested": [0.05, 0.10, 0.15],
            "dev_end": str(DEV_END),
            "oos_start": str(OOS_START),
        },
        "btc_fgi_audit": {
            "rows": int(len(btc)),
            "first_timestamp": str(btc["timestamp"].min()),
            "last_timestamp": str(btc["timestamp"].max()),
            "missing_safe_fgi": int(btc["fgi_safe"].isna().sum()),
        },
        "exchanges": {},
    }

    exchange_passes = []
    for exchange in ["bybit", "binance"]:
        try:
            oi, audit = load_oi(exchange)
            exch = {"oi_audit": audit, "sensitivity": {}}
            base_common = prepare_common(btc, oi, 0.10)
            slices = {
                "all": base_common,
                "dev": base_common[base_common["timestamp"] <= DEV_END].copy(),
                "oos": base_common[base_common["timestamp"] >= OOS_START].copy(),
            }
            exch["base_q10"] = {}
            for sname, sdf in slices.items():
                exch["base_q10"][sname] = {}
                for model in ["M0", "M1A", "M1B", "M2"]:
                    exch["base_q10"][sname][model] = evaluate_slice(sdf.reset_index(drop=True), model)
                exch["base_q10"][sname]["oi_edge_vs_m1b"] = compare_edge(
                    exch["base_q10"][sname]["M1B"], exch["base_q10"][sname]["M2"]
                )

            for q in [0.05, 0.10, 0.15]:
                common = prepare_common(btc, oi, q)
                oos = common[common["timestamp"] >= OOS_START].copy().reset_index(drop=True)
                exch["sensitivity"][str(q)] = evaluate_slice(oos, "M2")

            oos_edge = exch["base_q10"]["oos"]["oi_edge_vs_m1b"]
            oos_m2 = exch["base_q10"]["oos"]["M2"]
            neighbors_positive = all(
                m and m.get("total_return", -1) > 0 for m in exch["sensitivity"].values()
            )
            exchange_pass = bool(
                oos_edge.get("improved_count", 0) >= 4
                and oos_m2
                and oos_m2.get("total_return", -1) > 0
                and neighbors_positive
            )
            exch["gate"] = {
                "exchange_pass": exchange_pass,
                "oos_improved_metrics": oos_edge.get("improved_count", 0),
                "neighbor_percentiles_positive": neighbors_positive,
            }
            exchange_passes.append(exchange_pass)
            report["exchanges"][exchange] = exch
        except Exception as e:
            report["exchanges"][exchange] = {"error": f"{type(e).__name__}: {e}"}
            exchange_passes.append(False)

    if len(report["exchanges"]) == 2 and all(exchange_passes):
        verdict = "OI_ADDS_EDGE"
    elif any(exchange_passes):
        verdict = "INCONCLUSIVE_CROSS_EXCHANGE"
    else:
        verdict = "OI_DOES_NOT_ADD_EDGE_OR_DATA_GATE_FAILED"
    report["verdict"] = verdict

    report = finite_json(report)
    path = out / "btc_cross_exchange_backtest_r1_3_2.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== BTC CROWD/OI R1.3.2 ===")
    print("VERDICT:", verdict)
    for exchange, ex in report["exchanges"].items():
        print(f"\n[{exchange.upper()}]")
        if "error" in ex:
            print("ERROR:", ex["error"])
            continue
        print("OI AUDIT:", ex["oi_audit"])
        print("GATE:", ex["gate"])
        for model in ["M0", "M1A", "M1B", "M2"]:
            print(model, ex["base_q10"]["oos"][model])
        print("EDGE:", ex["base_q10"]["oos"]["oi_edge_vs_m1b"])
        print("SENSITIVITY:", ex["sensitivity"])
    print("ARTIFACT:", path)


if __name__ == "__main__":
    main()
