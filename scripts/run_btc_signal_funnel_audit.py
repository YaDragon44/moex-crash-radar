from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from run_btc_cross_exchange_backtest import (
    OOS_START,
    load_btc_fgi,
    load_oi,
    prepare_common,
)


def count_true(s: pd.Series) -> int:
    return int(s.fillna(False).astype(bool).sum())


def main() -> None:
    out = Path('artifacts')
    out.mkdir(exist_ok=True)
    btc = load_btc_fgi()
    oi, audit = load_oi('bybit')
    df = prepare_common(btc, oi, 0.10)
    df = df[df['timestamp'] >= OOS_START].copy().reset_index(drop=True)

    fear = df['fgi_safe'] <= 35
    reversal = df['fgi_reversal'].fillna(False)
    oi_stab = df['oi_stabilized'].fillna(False)
    price_confirm = df['price_confirm'].fillna(False)

    # Same risk admissibility used by the entry engine.
    risk_ok = (
        df['atr14'].notna()
        & df['prev_swing_low'].notna()
        & (df['atr14'] > 0)
        & ((df['close'] - (df['prev_swing_low'] - 0.5 * df['atr14'])) > 0)
        & ((df['close'] - (df['prev_swing_low'] - 0.5 * df['atr14'])) <= 2.0 * df['atr14'])
    )

    stages = [
        ('all_bars', pd.Series(True, index=df.index)),
        ('fear_le_35', fear),
        ('fear_plus_reversal', fear & reversal),
        ('fear_reversal_plus_oi_stabilized', fear & reversal & oi_stab),
        ('plus_price_confirmation', fear & reversal & oi_stab & price_confirm),
        ('plus_risk_gate', fear & reversal & oi_stab & price_confirm & risk_ok),
    ]

    funnel = []
    previous = None
    for name, mask in stages:
        n = count_true(mask)
        ratio_prev = None if previous in (None, 0) else n / previous
        ratio_all = n / len(df) if len(df) else 0
        funnel.append({
            'stage': name,
            'count': n,
            'retention_vs_previous': ratio_prev,
            'share_of_all_bars': ratio_all,
        })
        previous = n

    # Pairwise diagnostics: how restrictive each independent gate is inside fear+reversal.
    base = fear & reversal
    diagnostics = {
        'fear_reversal_count': count_true(base),
        'with_oi_stabilized': count_true(base & oi_stab),
        'with_price_confirmation': count_true(base & price_confirm),
        'with_risk_gate': count_true(base & risk_ok),
        'oi_stabilized_anywhere': count_true(oi_stab),
        'price_confirmation_anywhere': count_true(price_confirm),
        'risk_ok_anywhere': count_true(risk_ok),
    }

    report = {
        'release': 'R1.3.3',
        'exchange': 'bybit',
        'period': {'start': str(df['timestamp'].min()), 'end': str(df['timestamp'].max()), 'bars': len(df)},
        'oi_audit': audit,
        'funnel': funnel,
        'diagnostics': diagnostics,
    }
    path = out / 'btc_signal_funnel_audit_r1_3_3.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    print('=== BTC SIGNAL FUNNEL R1.3.3 ===')
    print('PERIOD:', report['period'])
    for x in funnel:
        print(x)
    print('DIAGNOSTICS:', diagnostics)
    print('ARTIFACT:', path)


if __name__ == '__main__':
    main()
