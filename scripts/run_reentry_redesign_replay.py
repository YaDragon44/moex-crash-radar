from __future__ import annotations

import json
from pathlib import Path
from statistics import median

ART = Path('artifacts')
SRC = ART / 'historical_evidence.json'
OUT = ART / 'reentry_redesign_replay.json'
WINDOW = 60
HORIZON = 20


def pct(a: float, b: float) -> float:
    return (b / a - 1.0) * 100.0


def main() -> None:
    payload = json.loads(SRC.read_text())
    rows = payload['daily_evidence']
    event_days = set(payload.get('frozen_exit_validation', {}).get('event_days') or [])
    if len(rows) < 500 or not event_days:
        raise SystemExit('R1.1.3 requires PIT daily evidence and frozen EXIT event days')
    event_idx = [i for i, r in enumerate(rows) if r['day'] in event_days]

    # R1.1.3 redesign: accumulation requires broad internal healing, not only a
    # falling aggregate Crash Score. All features are PIT and use only t and t-5.
    signals = []
    for ei in event_idx:
        saw_capitulation = False
        for i in range(ei, min(len(rows), ei + WINDOW + 1)):
            if i < 5:
                continue
            r, p = rows[i], rows[i - 5]
            score = float(r['score'])
            conf = int(r['critical_confirmations'])
            ret5 = pct(float(p['close']), float(r['close']))
            dscore = score - float(p['score'])

            capitulation = score >= 75 and conf >= 3 and ret5 <= -5.0
            if capitulation:
                saw_capitulation = True

            groups = {
                'stress_release': score <= 60 and dscore <= -15.0,
                'breadth_healing': float(r['breadth_score']) <= 55 and (float(r['breadth_score']) - float(p['breadth_score'])) <= -15.0,
                'structure_healing': float(r['market_structure_score']) <= 55 and (float(r['market_structure_score']) - float(p['market_structure_score'])) <= -15.0,
                'volatility_healing': float(r['volatility_liquidity_score']) <= 55 and (float(r['volatility_liquidity_score']) - float(p['volatility_liquidity_score'])) <= -10.0,
            }
            healing = sum(groups.values())
            accumulation = saw_capitulation and ret5 >= 0.0 and groups['stress_release'] and healing >= 3
            recovery = accumulation and score <= 45 and conf <= 1 and ret5 >= 3.0 and healing >= 3

            state = 'RECOVERY_WATCH_V2' if recovery else ('ACCUMULATION_WATCH_V2' if accumulation else ('CAPITULATION_WATCH' if capitulation else 'INACTIVE'))
            if state.startswith('ACCUMULATION') or state.startswith('RECOVERY'):
                end = min(len(rows), i + HORIZON + 1)
                future = rows[i:end]
                base = float(r['close'])
                rets = [pct(base, float(x['close'])) for x in future]
                signals.append({
                    'exit_day': rows[ei]['day'], 'day': r['day'], 'state': state,
                    'sessions_since_exit': i - ei, 'healing_groups': healing,
                    'groups': groups, 'score': round(score, 2), 'return_5d_pct': round(ret5, 2),
                    'forward_20row_min_return_pct': round(min(rets), 2),
                    'forward_20row_end_return_pct': round(rets[-1], 2),
                    'full_horizon': len(future) == HORIZON + 1,
                })
                break

    full = [s for s in signals if s['full_horizon']]
    mins = [s['forward_20row_min_return_pct'] for s in full]
    ends = [s['forward_20row_end_return_pct'] for s in full]
    positive_share = sum(x >= 0 for x in ends) / len(ends) if ends else None
    worst = min(mins) if mins else None

    # Same conservative quality policy as R1.1.2. This is a comparison gate,
    # not permission to promote to production.
    pass_drawdown = worst is not None and worst >= -15.0
    pass_positive = positive_share is not None and positive_share >= 0.60
    status = 'GO_FOR_BLIND_REENTRY_VALIDATION' if pass_drawdown and pass_positive and len(full) >= 4 else 'NO_GO_REDESIGN'

    out = {
        'release': 'R1.1.3 Re-entry Logic Redesign Replay',
        'status': status,
        'production_ready': False,
        'methodology': {
            'threshold_refit': False,
            'look_ahead_in_features': False,
            'design': 'Require post-capitulation context plus 3-of-4 independent healing groups; stress release is mandatory.',
            'groups': ['stress_release', 'breadth_healing', 'structure_healing', 'volatility_healing'],
            'note': 'Research redesign evaluated against the already-declared R1.1.2 quality policy; no production promotion.'
        },
        'metrics': {
            'signals': len(signals), 'full_horizon_signals': len(full),
            'median_forward_drawdown_pct': round(median(mins), 2) if mins else None,
            'worst_forward_drawdown_pct': round(worst, 2) if worst is not None else None,
            'median_forward_20row_end_return_pct': round(median(ends), 2) if ends else None,
            'nonnegative_20row_share': round(positive_share, 4) if positive_share is not None else None,
        },
        'gates': {'worst_drawdown_ge_minus_15': pass_drawdown, 'nonnegative_share_ge_60pct': pass_positive, 'min_full_horizon_signals_ge_4': len(full) >= 4},
        'signals': signals,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
