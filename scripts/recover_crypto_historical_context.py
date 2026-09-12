from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path('data/crypto-radar/historical_context_recovery.json')
LLAMA = 'https://stablecoins.llama.fi/stablecoincharts/all'


def finite(x):
    try:
        v = float(x)
        return math.isfinite(v)
    except Exception:
        return False


def get_json(url: str, timeout: int = 25):
    req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'crypto-crowd-radar-r1.7.2'})
    try:
        with urlopen(req, timeout=timeout) as r:
            return {'ok': True, 'status': r.status, 'data': json.load(r), 'error': None}
    except Exception as e:
        return {'ok': False, 'status': None, 'data': None, 'error': f'{type(e).__name__}: {e}'}


def stablecoin_audit():
    r = get_json(LLAMA)
    rows = r.get('data') if r.get('ok') and isinstance(r.get('data'), list) else []
    valid = 0
    times = []
    for x in rows:
        if not isinstance(x, dict):
            continue
        ts = x.get('date')
        total = x.get('totalCirculatingUSD') or x.get('totalCirculating')
        if finite(ts) and isinstance(total, dict):
            vals = [v for v in total.values() if finite(v)]
            if vals:
                valid += 1
                times.append(int(float(ts)))
    coverage = round(100 * valid / len(rows), 1) if rows else 0.0
    return {
        'source': 'DefiLlama',
        'endpoint': LLAMA,
        'status': 'AVAILABLE' if rows and valid else 'UNAVAILABLE',
        'rows': len(rows),
        'valid_rows': valid,
        'coverage_pct': coverage,
        'first_ts': min(times) if times else None,
        'last_ts': max(times) if times else None,
        'error': r.get('error'),
        'semantic': 'historical aggregate stablecoin market cap; suitable as liquidity-context history, not literal net inflow',
    }


def main():
    stable = stablecoin_audit()
    total = {
        'status': 'AUTH_REQUIRED',
        'preferred_source': 'CoinGecko',
        'endpoint': '/global/market_cap_chart',
        'plan_note': 'CoinGecko documentation marks global market-cap history as paid-plan only.',
        'fallbacks': [
            {'source': 'CoinMarketCap', 'endpoint': '/v1/global-metrics/quotes/historical', 'access': 'Hobbyist plan or higher'},
            {'source': 'Coinranking', 'endpoint': '/v2/stats/global-market-caps', 'access': 'Professional plan or higher'},
        ],
        'policy': 'Do not synthesize exact TOTAL from a partial coin basket.',
    }
    dominance = {
        'status': 'AUTH_REQUIRED',
        'preferred_method': 'BTC market cap / historical TOTAL from the same or quality-compatible source',
        'reason': 'Exact BTC.D requires historical total market cap. Current free live /global feed is not a historical series.',
        'policy': 'Do not scrape undocumented web payloads or substitute an approximate dominance series for exact-model validation.',
    }

    exact_context = stable['status'] == 'AVAILABLE' and total['status'] == 'AVAILABLE' and dominance['status'] == 'AVAILABLE'
    out = {
        'release': 'R1.7.2 Historical Market Context Recovery',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'features': {
            'stablecoin_market_cap_history': stable,
            'total_crypto_market_cap_history': total,
            'btc_dominance_history': dominance,
        },
        'gate': {
            'stablecoin_context_recovery': 'GO' if stable['status'] == 'AVAILABLE' and stable['coverage_pct'] >= 95 else 'NO-GO',
            'exact_full_context_recovery': 'GO' if exact_context else 'NO-GO',
            'full_model_historical_replay': 'GO' if exact_context else 'BLOCKED_EXTERNAL_DATA',
            'decision': 'PARTIAL',
            'reason': 'Stablecoin history is recoverable free via DefiLlama. Exact TOTAL and BTC.D remain blocked by authenticated historical-global-metrics access.',
        },
        'recommended_path': {
            'simple': 'Keep current live collection accumulating TOTAL/BTC.D while using DefiLlama for stablecoin history. Do not calibrate full model yet.',
            'fastest_full_replay': 'Connect one paid historical global-metrics source (prefer CoinGecko to stay closest to current live semantics), then rerun exact full-model replay.',
            'prohibited': ['approximate TOTAL from top-N coins', 'undocumented scraping as canonical source', 'threshold tuning on partial derivatives replay'],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'gate': out['gate'], 'stablecoin_rows': stable['rows'], 'stablecoin_coverage_pct': stable['coverage_pct']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
