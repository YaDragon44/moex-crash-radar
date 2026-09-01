# R1.4.1 — Public Technical Validation

Period: 2026-06-01 .. 2026-09-01, 1H, forward horizon = 4 bars.

Scope: public technical stack only. OI/FUTOI/Legal-FIZ excluded.

## Aggregate result

| Model | Signals | Mean signed 4H return | Hit rate |
|---|---:|---:|---:|
| T0 Trend + Trigger | 2,782 | +4.09 bps | 50.61% |
| T1 + RVOL >= 1.20 | 1,588 | +3.98 bps | 49.81% |
| T2 + RSI regime | 437 | +2.09 bps | 51.03% |
| FULL RVOL + RSI | 244 | -2.59 bps | 47.95% |

## Market-specific observations

- MX: RVOL modestly improves mean; RSI improves hit-rate but reduces mean; FULL is almost flat.
- SI: RSI and FULL materially worsen quality.
- SR: FULL mean is positive but sample is only 28 and hit-rate is 50%; not robust.
- GZ: RSI alone improves mean, but FULL turns negative.
- BR: RSI and FULL materially worsen a strong base signal.
- MMU: filters do not materially improve the base signal.
- CRU: RVOL and RSI both improve the sample; FULL is strongest, but only 16 signals.
- NG: all variants are negative; this family should not inherit the same directional entry rule without separate calibration.
- RN: RVOL improves mean but median remains negative.
- TB: RSI improves mean/hit-rate; FULL remains positive but small sample.
- SVU: data fetch failed in this run; status N/A, no inference.

## Gate conclusion

**Universal FULL gate = NO-GO.**

The evidence does not support using RVOL and RSI as mandatory binary filters across all MOEX futures. The simplest Trend + confirmed Price Trigger is the most stable broad baseline in this sample.

Recommended R1.4.2 rule redesign:

1. QUALITY remains a hard gate.
2. TREND remains a hard gate.
3. PRICE TRIGGER remains a hard gate.
4. RVOL becomes a context/confidence feature, not a universal veto.
5. RSI becomes a context/late-entry warning feature, not a universal veto.
6. OI and Legal/FIZ, when point-in-time data is available, remain a separate positioning-confirmation layer and must not be claimed as validated by this release.
7. NG and any other persistently negative family require market-specific calibration or exclusion.

This is an entry-quality screen, not a net PnL backtest; fees, slippage, stop/exit logic and roll-chain are outside this release.
