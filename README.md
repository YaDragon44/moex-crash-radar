# MOEX Crash Early Warning Radar

Система раннего предупреждения изменения риска российского рынка акций: обнаружить переход режима раньше, чем он становится очевиден по цене, снизить риск капитала и затем дождаться подтверждённого re-entry.

## Current release
R0.4.3 — Analytical UX Completion (IN TEST)

## Core architecture
DATA → QUALITY GATE → FEATURES → MARKET/CROWD EVIDENCE → RISK → TRANSITION → REGIME → ACTION → DASHBOARD.

Static frontend + GitHub Pages + GitHub Actions + public market sources. Dedicated backend is not required for the current release.

## R0.3.3 calibrated EXIT Gate
Historical MOEX evidence uses point-in-time features without look-ahead.

Gate parameters:
- Crash Score threshold: 65
- critical confirmations: 3
- persistence: 2
- 5D return confirmation: <= -3%
- cooldown: 30 evidence rows
- rearm clear rows: 3

Historical calibration result:
- detected clean crisis episodes: 4/4
- false event rate: 28.57%
- median lead time: 28.5 calendar days
- calibration exit events: 14, false events: 4

Important limitation: breadth history uses a present-day liquid basket rather than historical index constituents. Historical results therefore retain survivorship/listing-history bias and are calibration evidence, not unbiased production performance.

## R0.4.3 dashboard
The approved Russian-language one-screen dashboard now includes:
- Crash Score, current EXIT stage, CASH signal and IMOEX;
- exactly 9 key indicator cards with strict LIVE / DELAYED / STALE / ERROR / N/A handling;
- real Crash Score history from point-in-time evidence;
- Historical Gate metrics;
- separate blocks: Выводы / Гипотезы / Рекомендации;
- separate Investor Action and Trader Action;
- WHY: three strongest available factors behind current action;
- responsive 16:9-first layout.

The analytical UX never fabricates missing market or macro data. Unsourced Rate/OFZ, Oil/RUB, Macro/Earnings, News/Geopolitics and Bottom Engine inputs remain N/A. Strong recommendations are blocked when the Quality Gate is insufficient.

## Next gate
R0.4.3 requires CI, live MOEX snapshot contract validation and GitHub Pages deployment before GO.
