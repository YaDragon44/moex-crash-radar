from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from moex_crash_radar.breadth import breadth_signal, calculate_breadth, index_vs_breadth_divergence
from moex_crash_radar.context import calculate_context
from moex_crash_radar.distribution import calculate_distribution, distribution_signal
from moex_crash_radar.engine import calculate_crash, crash_momentum
from moex_crash_radar.features import derive_index_signals
from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.live_gate import CALIBRATED_EXIT_GATE, exit_gate_status
from moex_crash_radar.moex import fetch_index_candles, fetch_share_candles
from moex_crash_radar.oil_rub import collect_oil_rub
from moex_crash_radar.rate_ofz import collect_rate_ofz

BREADTH_UNIVERSE=("SBER","SBERP","LKOH","GAZP","YDEX","T","X5","GMKN","NVTK","ROSN","TATN","TATNP","PLZL","CHMF","NLMK","ALRS","MOEX","MTSS","PHOR","IRAO","HYDR","AFLT","VKCO","OZON")

def main()->None:
    end=date.today(); start=end-timedelta(days=500)
    index_candles=fetch_index_candles("IMOEX",start=start.isoformat(),end=end.isoformat())
    if not index_candles: raise SystemExit("MOEX returned no IMOEX candles")
    market_signals=derive_index_signals(index_candles); universe={}; failed=[]
    for secid in BREADTH_UNIVERSE:
        try:
            candles=fetch_share_candles(secid,start=start.isoformat(),end=end.isoformat())
            if len(candles)>=51: universe[secid]=candles
            else: failed.append(secid)
        except Exception: failed.append(secid)
    breadth=calculate_breadth(universe); breadth_payload=None; breadth_coverage=0.0
    if breadth is not None:
        breadth_coverage=breadth.usable_size/len(BREADTH_UNIVERSE)
        breadth_payload={"universe_size":len(BREADTH_UNIVERSE),"usable_size":breadth.usable_size,"coverage":round(breadth_coverage,4),"pct_above_ma20":breadth.pct_above_ma20,"pct_above_ma50":breadth.pct_above_ma50,"pct_new_20d_lows":breadth.pct_new_20d_lows,"pct_new_20d_highs":breadth.pct_new_20d_highs,"advance_decline_ratio":breadth.advance_decline_ratio,"breadth_return_5d":breadth.breadth_return_5d,"index_vs_breadth_divergence":index_vs_breadth_divergence(index_candles,breadth),"failed_secids":failed}
        if breadth.usable_size>=12 and breadth_coverage>=.50: market_signals["breadth"]=breadth_signal(breadth)
    distribution=calculate_distribution(universe); distribution_payload=None
    if distribution is not None:
        distribution_payload={"usable_size":distribution.usable_size,"pct_down_rvol":distribution.pct_down_rvol,"pct_distribution_5d":distribution.pct_distribution_5d,"mean_down_up_volume_ratio":distribution.mean_down_up_volume_ratio}
        if distribution.usable_size>=12 and breadth_coverage>=.50: market_signals["volume_distribution"]=distribution_signal(distribution)

    # Keep R0.3.3 EXIT gate market-only until a separate context-aware historical revalidation.
    crash=calculate_crash(market_signals)
    rate_ofz=collect_rate_ofz(as_of=end); oil_rub=collect_oil_rub(as_of=end)
    context_signals={}
    if rate_ofz.signal is not None: context_signals["rate_ofz"]=rate_ofz.signal
    if oil_rub.signal is not None: context_signals["oil_rub"]=oil_rub.signal
    context=calculate_context(context_signals)

    evidence=build_daily_evidence(index_candles,universe,min_equity_coverage=.50,warmup=60); exit_gate=exit_gate_status(evidence)
    score_history=[x.score for x in evidence if x.score is not None]; momentum=crash_momentum(score_history,5) if len(score_history)>5 else None
    crash_history=[{"day":x.day,"score":x.score,"state":x.state} for x in evidence[-120:] if x.score is not None]
    display_signals=dict(market_signals)
    if rate_ofz.signal is not None: display_signals["rate_ofz"]=rate_ofz.signal
    if oil_rub.signal is not None: display_signals["oil_rub"]=oil_rub.signal

    rate_group={"score":rate_ofz.signal.score if rate_ofz.signal else None,"quality":rate_ofz.signal.quality.value if rate_ofz.signal else "N/A","key_rate":rate_ofz.key_rate,"key_rate_day":rate_ofz.key_rate_day,"median_long_ofz_yield":rate_ofz.median_long_ofz_yield,"ofz_count":rate_ofz.ofz_count,"rgbi_return_5d":rate_ofz.rgbi_return_5d,"rgbi_return_20d":rate_ofz.rgbi_return_20d,"component_coverage":rate_ofz.component_coverage,"note":rate_ofz.note,"sources":["Bank of Russia","MOEX ISS TQOB","MOEX ISS RGBI"]}
    oil_group={"score":oil_rub.signal.score if oil_rub.signal else None,"quality":oil_rub.signal.quality.value if oil_rub.signal else "N/A","brent_secid":oil_rub.brent_secid,"brent_return_5d":oil_rub.brent_return_5d,"brent_return_20d":oil_rub.brent_return_20d,"cnyrub_return_5d":oil_rub.cnyrub_return_5d,"cnyrub_return_20d":oil_rub.cnyrub_return_20d,"component_coverage":oil_rub.component_coverage,"latest_day":oil_rub.latest_day,"note":oil_rub.note,"sources":["MOEX ISS FORTS Brent","MOEX ISS CNYRUB_TOM"]}

    payload={"release":"R0.5.2 Oil / RUB Live Integration","as_of":index_candles[-1].begin,"source":"MOEX ISS","secid":"IMOEX","last_close":index_candles[-1].close,"data_quality":crash.quality.value,"signals":{k:{"score":v.score,"quality":v.quality.value} for k,v in display_signals.items()},"breadth":breadth_payload,"volume_distribution":distribution_payload,
      "context":{"score":context.score,"state":context.state.value,"quality":context.quality.value,"coverage":context.coverage,"available_groups":context.available_groups,"total_groups":context.total_groups,"groups":{"rate_ofz":rate_group,"oil_rub":oil_group,"macro_earnings":{"score":None,"quality":"N/A"},"news_geopolitics":{"score":None,"quality":"N/A"}},"note":"Independent external-risk layer. Rate/OFZ + Oil/RUB can unlock Context only through multi-group Quality Gate; Context is not a probability and not Crowd Score."},
      "crash":{"score":crash.score,"state":crash.state.value,"available_weight":round(crash.available_weight,4),"critical_confirmations":crash.critical_confirmations,"raw_cash_signal":crash.cash_signal},"exit_gate":exit_gate,"crash_momentum":momentum,"crash_history":crash_history,"bottom":{"score":None,"state":"DATA_INSUFFICIENT","buy_back_signal":False},
      "calibration":{"release":"R0.3.3","false_event_rate":.2857,"detected_episodes":"4/4","median_lead_days":28.5,"total_exit_events":14,"false_exit_events":4,"params":{"score_threshold":CALIBRATED_EXIT_GATE.score_threshold,"confirmations":CALIBRATED_EXIT_GATE.confirmations,"persistence":CALIBRATED_EXIT_GATE.persistence,"max_5d_return_pct":CALIBRATED_EXIT_GATE.max_5d_return_pct,"cooldown_rows":CALIBRATED_EXIT_GATE.cooldown_rows,"rearm_clear_rows":CALIBRATED_EXIT_GATE.rearm_clear_rows},"warning":"Historical breadth has survivorship/listing-history bias. R0.5 context remains outside calibrated R0.3.3 EXIT gate until re-validation."},
      "note":"R0.5.2 activates Rate/OFZ and Oil/RUB context from CBR/MOEX public sources. Macro/news and Bottom Engine remain N/A; missing data is never invented."}
    out=Path("artifacts/market_snapshot.json"); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); print(out)

if __name__=="__main__": main()
