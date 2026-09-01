# R1.4 Simple Entry Radar

One-screen MOEX 1H scanner for 13 markets:

`MX / Si / SBER / GD / BR / MMU / CRU / SVU / NG / GAZP / ROSN / T / Silver`

Current instrument mapping for the September 2026 contract cycle:

- MX -> MXU6
- Si -> SiU6
- SBER -> SRU6
- GD -> GDU6
- BR -> BRU6
- MMU -> MMU6
- CRU -> CRU6
- SVU -> SVU6
- NG -> NGU6
- GAZP -> GZU6
- ROSN -> RNU6
- T -> TBU6
- Silver -> SLVRUBF (separate perpetual RUB-silver line)

The browser loads public 1H MOEX ISS candles and computes EMA20/50, RSI(14), RVOL and price trigger. OI delta is used only when the candle feed exposes an OI/open-position field.

## Strong signal gate

LONG:
- EMA20 > EMA50
- EMA20 slope up
- price > EMA20
- OI delta >= +0.50%
- Legal net delta > 0 AND Retail net delta < 0
- RVOL >= 1.20
- RSI(14) 55..65 and rising
- close > previous 1H high

SHORT is symmetric, with RSI 35..45 and falling.

`Legal/FIZ` is fail-closed. The UI never invents or approximates participant positioning. When it is unavailable, the strongest possible state is `SETUP FORMING`.

## Optional positions.json

The dashboard attempts to read `positions.json` in the same directory. Expected structure:

```json
{
  "MX": {"legal_net_delta": 1000, "retail_net_delta": -800},
  "SiU6": {"legal_net_delta": -5000, "retail_net_delta": 4200}
}
```

Use only point-in-time values whose publication time is known to be available before the decision timestamp. Do not forward-fill stale positioning.

## States

- `NO ENTRY`
- `SETUP FORMING`
- `STRONG LONG`
- `STRONG SHORT`
- `DATA N/A`

This is a monitoring/research release. Thresholds are hypotheses until historical validation.