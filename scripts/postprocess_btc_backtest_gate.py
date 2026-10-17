import json
from pathlib import Path

PATH = Path('artifacts/btc_cross_exchange_backtest_r1_3_2.json')
report = json.loads(PATH.read_text(encoding='utf-8'))

MIN_OI_BARS = 1000
MIN_OOS_TRADES = 10
reasons = []

for exchange, ex in report.get('exchanges', {}).items():
    if 'error' in ex:
        reasons.append(f'{exchange}: data error: {ex["error"]}')
        continue
    bars = int(ex.get('oi_audit', {}).get('rows', 0) or 0)
    if bars < MIN_OI_BARS:
        reasons.append(f'{exchange}: only {bars} OI bars (<{MIN_OI_BARS})')
    m2 = ex.get('base_q10', {}).get('oos', {}).get('M2', {})
    trades = int(m2.get('trades', 0) or 0) if m2 else 0
    if trades < MIN_OOS_TRADES:
        reasons.append(f'{exchange}: only {trades} OOS M2 trades (<{MIN_OOS_TRADES})')

if reasons:
    report['raw_runner_verdict'] = report.get('verdict')
    report['verdict'] = 'INCONCLUSIVE_INSUFFICIENT_EVIDENCE'
    report['evidence_gate'] = {
        'pass': False,
        'min_oi_bars': MIN_OI_BARS,
        'min_oos_m2_trades': MIN_OOS_TRADES,
        'reasons': reasons,
    }
else:
    report['evidence_gate'] = {
        'pass': True,
        'min_oi_bars': MIN_OI_BARS,
        'min_oos_m2_trades': MIN_OOS_TRADES,
        'reasons': [],
    }

PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('FINAL VERDICT:', report['verdict'])
print('EVIDENCE GATE:', report['evidence_gate'])
