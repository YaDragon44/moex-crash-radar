from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

UNIVERSE = {
    'MX': 'MXU6', 'Si': 'SiU6', 'SBER': 'SRU6', 'GD': 'GDU6', 'BR': 'BRU6',
    'MMU': 'MMU6', 'CRU': 'CRU6', 'SVU': 'SVU6', 'NG': 'NGU6', 'GAZP': 'GZU6',
    'ROSN': 'RNU6', 'T': 'TBU6', 'Silver': 'SLVRUBF'
}
START = '2026-06-01'
END = '2026-09-01'
HORIZON = 8
STOPS = ('SIGNAL_CANDLE', 'ATR_1_0', 'ATR_1_5', 'SWING_3')


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'moex-crash-radar/1.4.3.1'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def candles(secid: str) -> list[dict]:
    q = urllib.parse.urlencode({'iss.meta': 'off', 'interval': 60, 'from': START, 'till': END})
    url = f'https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities/{secid}/candles.json?{q}'
    j = get_json(url)['candles']
    cols = j['columns']
    return [dict(zip(cols, row)) for row in j['data'] if row[cols.index('close')] is not None]


def ema(values: list[float], n: int) -> float:
    if len(values) < n:
        return math.nan
    e = sum(values[:n]) / n
    k = 2 / (n + 1)
    for x in values[n:]:
        e = x * k + e * (1 - k)
    return e


def wilder_atr(rows: list[dict], n: int = 14) -> list[float]:
    out = [math.nan] * len(rows)
    trs = []
    for i, r in enumerate(rows):
        h, l = float(r['high']), float(r['low'])
        if i == 0:
            tr = h - l
        else:
            pc = float(rows[i - 1]['close'])
            tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
        if i == n - 1:
            out[i] = sum(trs[:n]) / n
        elif i >= n:
            out[i] = ((out[i - 1] * (n - 1)) + tr) / n
    return out


def direction(rows: list[dict], i: int) -> str:
    closes = [float(r['close']) for r in rows[: i + 1]]
    if len(closes) < 51:
        return 'NONE'
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    e20p = ema(closes[:-1], 20)
    px = closes[-1]
    if e20 > e50 and e20 > e20p and px > e20:
        return 'LONG'
    if e20 < e50 and e20 < e20p and px < e20:
        return 'SHORT'
    return 'NONE'


def stop_level(rows: list[dict], i: int, entry: float, atr: float, side: str, model: str) -> float:
    signal = rows[i]
    if model == 'SIGNAL_CANDLE':
        return float(signal['low'] if side == 'LONG' else signal['high'])
    if model == 'ATR_1_0':
        return entry - atr if side == 'LONG' else entry + atr
    if model == 'ATR_1_5':
        return entry - 1.5 * atr if side == 'LONG' else entry + 1.5 * atr
    if model == 'SWING_3':
        window = rows[max(0, i - 2): i + 1]
        return min(float(x['low']) for x in window) if side == 'LONG' else max(float(x['high']) for x in window)
    raise ValueError(model)


def signed_return(side: str, entry: float, px: float) -> float:
    raw = (px / entry - 1.0) * 10000
    return raw if side == 'LONG' else -raw


def evaluate(rows: list[dict]) -> list[dict]:
    atrs = wilder_atr(rows)
    events = []
    for i in range(51, len(rows) - HORIZON - 1):
        side = direction(rows, i)
        if side == 'NONE':
            continue
        prev = rows[i - 1]
        close = float(rows[i]['close'])
        trigger = float(prev['high'] if side == 'LONG' else prev['low'])
        trig = close > trigger if side == 'LONG' else close < trigger
        if not trig:
            continue
        entry = float(rows[i + 1]['open'])
        atr = atrs[i]
        if not math.isfinite(atr) or atr <= 0 or entry <= 0:
            continue
        future = rows[i + 1: i + 1 + HORIZON]
        mfe = max(signed_return(side, entry, float(x['high'] if side == 'LONG' else x['low'])) for x in future)
        mae = min(signed_return(side, entry, float(x['low'] if side == 'LONG' else x['high'])) for x in future)
        event = {'side': side, 'entry': entry, 'mfe_bps': mfe, 'mae_bps': mae, 'stops': {}}
        for model in STOPS:
            sl = stop_level(rows, i, entry, atr, side, model)
            risk_bps = abs(sl / entry - 1.0) * 10000
            hit = False
            exit_bps = None
            hit_bar = None
            for k, bar in enumerate(future, start=1):
                touched = float(bar['low']) <= sl if side == 'LONG' else float(bar['high']) >= sl
                if touched:
                    hit = True
                    hit_bar = k
                    exit_bps = -risk_bps
                    break
            if not hit:
                exit_bps = signed_return(side, entry, float(future[-1]['close']))
            event['stops'][model] = {'risk_bps': risk_bps, 'hit': hit, 'hit_bar': hit_bar, 'exit_8h_bps': exit_bps}
        events.append(event)
    return events


def summarize(events: list[dict]) -> dict:
    out = {'signals': len(events), 'models': {}}
    if not events:
        return out
    out['baseline_8h_mean_bps'] = statistics.fmean(
        e['stops']['ATR_1_5']['exit_8h_bps'] if not e['stops']['ATR_1_5']['hit'] else e['stops']['ATR_1_5']['exit_8h_bps'] for e in events
    )
    out['mfe_mean_bps'] = statistics.fmean(e['mfe_bps'] for e in events)
    out['mae_mean_bps'] = statistics.fmean(e['mae_bps'] for e in events)
    for m in STOPS:
        vals = [e['stops'][m] for e in events]
        exits = [x['exit_8h_bps'] for x in vals]
        out['models'][m] = {
            'n': len(vals),
            'mean_risk_bps': round(statistics.fmean(x['risk_bps'] for x in vals), 2),
            'stop_hit_rate_pct': round(100 * sum(x['hit'] for x in vals) / len(vals), 2),
            'mean_8h_exit_bps': round(statistics.fmean(exits), 2),
            'median_8h_exit_bps': round(statistics.median(exits), 2),
            'positive_exit_pct': round(100 * sum(x > 0 for x in exits) / len(exits), 2),
        }
    return out


def main() -> None:
    report = {'release': 'R1.4.3.1', 'period': [START, END], 'instruments': {}, 'aggregate': {}}
    all_events = []
    for label, secid in UNIVERSE.items():
        try:
            rows = candles(secid)
            events = evaluate(rows)
            report['instruments'][label] = {'secid': secid, **summarize(events)}
            all_events.extend(events)
        except Exception as e:
            report['instruments'][label] = {'secid': secid, 'status': 'ERROR', 'error': repr(e)}
    report['aggregate'] = summarize(all_events)
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/r1_4_3_1_stop_gate.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = ['# R1.4.3.1 Historical Stop Gate', '', f'Period: {START} → {END}', '']
    a = report['aggregate']
    lines.append(f"Signals: **{a.get('signals', 0)}**")
    lines.append('')
    lines.append('| Stop | N | Mean risk, bps | Stop hit % | Mean 8H exit, bps | Median, bps | Positive % |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|')
    for m, s in a.get('models', {}).items():
        lines.append(f"| {m} | {s['n']} | {s['mean_risk_bps']} | {s['stop_hit_rate_pct']} | {s['mean_8h_exit_bps']} | {s['median_8h_exit_bps']} | {s['positive_exit_pct']} |")
    lines += ['', '## Per instrument']
    for label, r in report['instruments'].items():
        if r.get('status') == 'ERROR':
            lines.append(f'- {label}: ERROR — {r["error"]}')
        else:
            best = max(r.get('models', {}).items(), key=lambda kv: kv[1]['mean_8h_exit_bps'], default=(None, None))
            lines.append(f"- {label}: n={r.get('signals',0)}; best mean 8H={best[0]} {best[1]['mean_8h_exit_bps']} bps" if best[0] else f'- {label}: n=0')
    Path('artifacts/r1_4_3_1_stop_gate.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
