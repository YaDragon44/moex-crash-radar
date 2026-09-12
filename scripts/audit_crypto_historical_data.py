from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUT = Path('data/crypto-radar/historical_audit.json')
BASE = 'https://api.gateio.ws/api/v4'


def get_json(url: str, timeout: int = 20):
    req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'crypto-crowd-radar-r1.7-audit'})
    try:
        with urlopen(req, timeout=timeout) as r:
            return {'ok': True, 'status': r.status, 'data': json.load(r), 'error': None}
    except Exception as e:
        return {'ok': False, 'status': None, 'data': None, 'error': f'{type(e).__name__}: {e}'}


def finite(x):
    try:
        v = float(x)
        return math.isfinite(v)
    except Exception:
        return False


def endpoint(path: str, params: dict):
    return f"{BASE}{path}?{urlencode(params)}"


def summarize(result: dict, required_fields: tuple[str, ...], ts_field: str):
    rows = result.get('data') if result.get('ok') else None
    rows = rows if isinstance(rows, list) else []
    valid = 0
    times = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if all(row.get(k) is not None for k in required_fields):
            valid += 1
        if finite(row.get(ts_field)):
            times.append(int(float(row[ts_field])))
    return {
        'source': 'Gate.io',
        'status': 'AVAILABLE' if result.get('ok') and rows and valid > 0 else 'UNAVAILABLE',
        'rows': len(rows),
        'valid_rows': valid,
        'coverage_pct': round(valid / len(rows) * 100, 1) if rows else 0.0,
        'first_ts': min(times) if times else None,
        'last_ts': max(times) if times else None,
        'error': result.get('error'),
        'required_fields': list(required_fields),
    }


def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    frm = int(start.timestamp())
    to = int(now.timestamp())

    candles = get_json(endpoint('/futures/usdt/candlesticks', {
        'contract': 'BTC_USDT', 'from': frm, 'to': to, 'interval': '1h'
    }))
    stats = get_json(endpoint('/futures/usdt/contract_stats', {
        'contract': 'BTC_USDT', 'from': frm, 'interval': '1h', 'limit': 1000
    }))
    funding = get_json(endpoint('/futures/usdt/funding_rate', {
        'contract': 'BTC_USDT', 'from': frm, 'to': to, 'limit': 1000
    }))

    audit = {
        'release': 'R1.7.0 Historical Data Audit',
        'generated_at': now.isoformat(),
        'window_days': 30,
        'target_model': 'current Crypto Radar Crowd/Risk/Regime rules',
        'features': {
            'btc_price_1h': summarize(candles, ('t', 'c'), 't'),
            'open_interest_and_long_short_1h': summarize(stats, ('time', 'open_interest_usd', 'lsr_account'), 'time'),
            'funding_history': summarize(funding, ('t', 'r'), 't'),
            'total_crypto_market_cap_history': {
                'source': 'current source set', 'status': 'MISSING', 'reason': 'Current live CoinGecko /global feed does not provide historical TOTAL series in the existing implementation.'
            },
            'btc_dominance_history': {
                'source': 'current source set', 'status': 'MISSING', 'reason': 'Current live CoinGecko /global feed does not provide historical BTC dominance series in the existing implementation.'
            },
            'stablecoin_market_cap_delta_history': {
                'source': 'current source set', 'status': 'MISSING', 'reason': 'Existing stablecoin proxy is computed from current 24h market-cap changes; no persistent historical series existed before R1.6.'
            },
            'news_history': {'status': 'MISSING', 'reason': 'Not present in current live MVP and therefore excluded rather than imputed.'},
            'liquidation_proxy_history': {'status': 'MISSING', 'reason': 'Current Crowd MVP does not have a live liquidation factor; no historical value is fabricated.'},
        },
    }

    deriv_ok = all(
        audit['features'][k]['status'] == 'AVAILABLE' and audit['features'][k].get('coverage_pct', 0) >= 95
        for k in ('btc_price_1h','open_interest_and_long_short_1h','funding_history')
    )
    exact_model_ok = deriv_ok and all(audit['features'][k]['status'] == 'AVAILABLE' for k in (
        'total_crypto_market_cap_history','btc_dominance_history','stablecoin_market_cap_delta_history'
    ))
    audit['gate'] = {
        'derivatives_shadow_replay': 'GO' if deriv_ok else 'NO-GO',
        'exact_full_model_replay': 'GO' if exact_model_ok else 'NO-GO',
        'decision': 'PARTIAL' if deriv_ok and not exact_model_ok else ('GO' if exact_model_ok else 'NO-GO'),
        'reason': 'Run a derivatives-only SHADOW replay if Gate historical data has >=95% field coverage. Do not call it validation of the full live model until historical market-context series are sourced and quality-gated.' if deriv_ok and not exact_model_ok else 'See feature coverage.',
    }
    audit['next_step'] = {
        'release': 'R1.7.1 Derivatives Shadow Replay' if deriv_ok else 'Historical Source Recovery',
        'rule': 'No threshold calibration from partial replay; use only for transition/noise diagnostics.'
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'gate': audit['gate'], 'coverage': {k: audit['features'][k].get('coverage_pct') for k in ('btc_price_1h','open_interest_and_long_short_1h','funding_history')}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
