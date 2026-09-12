from __future__ import annotations
import json, math, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CG_GLOBAL = "https://api.coingecko.com/api/v3/global"
CG_STABLE = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=stablecoins&order=market_cap_desc&per_page=250&page=1&sparkline=false&price_change_percentage=24h"
GATE_TICKER = "https://api.gateio.ws/api/v4/futures/usdt/tickers?contract=BTC_USDT"
GATE_STATS = "https://api.gateio.ws/api/v4/futures/usdt/contract_stats?contract=BTC_USDT&interval=1h&limit=25"
OUT = Path("data/crypto-radar/snapshot.json")

def num(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None

def get_json(url, timeout=12):
    req=Request(url, headers={"Accept":"application/json","User-Agent":"crypto-crowd-radar/1.4.1"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return {"ok": True, "data": json.load(r), "error": None}
    except Exception as e:
        return {"ok": False, "data": None, "error": f"{type(e).__name__}: {e}"}

def funding_score(x):
    if x is None: return None
    if x <= -0.03: return 10
    if x <= -0.01: return 25
    if x < 0.01: return 50
    if x < 0.03: return 75
    return 90

def ls_score(r):
    if r is None or r <= 0: return None
    if r < .80: return 15
    if r < .95: return 30
    if r <= 1.05: return 50
    if r <= 1.20: return 70
    return 85

def flow_score(x):
    if x is None: return None
    if x <= -.20: return 20
    if x <= -.05: return 35
    if x < .05: return 50
    if x < .20: return 65
    return 80

def oi_price_score(p,o):
    if p is None or o is None: return None
    if abs(o)<1: return 60 if p>=2 else 40 if p<=-2 else 50
    if p>0 and o>0: return 90 if o>=8 else 80 if o>=4 else 70
    if p>0 and o<0: return 55
    if p<0 and o>0: return 10 if o>=8 else 20 if o>=4 else 30
    if p<0 and o<0: return 35
    return 50

def state_action(score):
    if score is None: return "N/A","NO DATA"
    if score<=24: return "PANIC","WAIT"
    if score<=39: return "FEAR","WATCH"
    if score<=60: return "NEUTRAL","WAIT"
    if score<=75: return "GREED","REDUCE"
    return "EUPHORIA","NO CHASE"

def build(results):
    cg, stable, ticker, stats = (results[k] for k in ("cg","stable","ticker","stats"))
    total=btcd=total24=btc_cap=alt_cap=None
    if cg["ok"] and isinstance(cg["data"],dict):
        d=cg["data"].get("data") or {}
        total=num((d.get("total_market_cap") or {}).get("usd"))
        btcd=num((d.get("market_cap_percentage") or {}).get("btc"))
        total24=num(d.get("market_cap_change_percentage_24h_usd"))
        if total is not None and btcd is not None:
            btc_cap=total*btcd/100
            alt_cap=total-btc_cap

    price=p24=funding=oi_now=oi_old=oi_delta=lsr=None
    if ticker["ok"] and isinstance(ticker["data"],list) and ticker["data"]:
        t=ticker["data"][0]
        price=num(t.get("last"))
        p24=num(t.get("change_percentage"))
        funding=num(t.get("funding_rate"))
        if funding is not None: funding*=100

    if stats["ok"] and isinstance(stats["data"],list) and stats["data"]:
        rows=stats["data"][:]
        if all(num(x.get("time")) is not None for x in rows):
            rows.sort(key=lambda x: num(x.get("time")))
        first,last=rows[0],rows[-1]
        oi_old=num(first.get("open_interest_usd"))
        oi_now=num(last.get("open_interest_usd"))
        lsr=num(last.get("lsr_account"))
        if oi_old and oi_now is not None:
            oi_delta=(oi_now/oi_old-1)*100

    stable_cap=stable_delta=None
    if stable["ok"] and isinstance(stable["data"],list):
        cur=prev=0.0; usable=0
        for c in stable["data"]:
            mc=num(c.get("market_cap")); ch=num(c.get("market_cap_change_percentage_24h"))
            if mc is not None and mc>0 and ch is not None and ch>-99.9:
                cur+=mc; prev+=mc/(1+ch/100); usable+=1
        if usable>=5 and cur>0 and prev>0:
            stable_cap=cur
            stable_delta=(cur/prev-1)*100

    factors={
        "oi_price":oi_price_score(p24,oi_delta),
        "funding":funding_score(funding),
        "long_short":ls_score(lsr),
        "liquidation_risk":None,
        "news":None,
        "flows":flow_score(stable_delta),
    }
    weights={"oi_price":.20,"funding":.20,"long_short":.15,"liquidation_risk":.15,"news":.15,"flows":.15}
    present=[k for k,v in factors.items() if v is not None]
    coverage=sum(weights[k] for k in present)*100
    derivatives=sum(k in {"oi_price","funding","long_short","liquidation_risk"} for k in present)
    external=any(k in {"news","flows"} for k in present)
    quality=(p24 is not None and coverage>=70 and derivatives>=2 and external)
    score=None
    if quality:
        sw=sum(weights[k] for k in present)
        score=round(sum(weights[k]*factors[k] for k in present)/sw)
    crowd_state,action=state_action(score)

    now=datetime.now(timezone.utc).isoformat()
    return {
      "version":"1.4.1",
      "generated_at":now,
      "source_status":{
        "coingecko_global":"LIVE" if cg["ok"] else "N/A",
        "coingecko_stablecoins":"LIVE" if stable["ok"] else "N/A",
        "gate_ticker":"LIVE" if ticker["ok"] else "N/A",
        "gate_contract_stats":"LIVE" if stats["ok"] else "N/A",
      },
      "source_errors":{
        "coingecko_global":None if cg["ok"] else cg["error"],
        "coingecko_stablecoins":None if stable["ok"] else stable["error"],
        "gate_ticker":None if ticker["ok"] else ticker["error"],
        "gate_contract_stats":None if stats["ok"] else stats["error"],
      },
      "market":{"total_market_cap":total,"total_change_24h_pct":total24,"btc_dominance_pct":btcd,"btc_cap":btc_cap,"alt_cap":alt_cap},
      "derivatives":{"btc_price":price,"price_change_24h_pct":p24,"oi_usd":oi_now,"oi_change_24h_pct":oi_delta,"funding_pct":funding,"long_short_ratio":lsr},
      "context":{"stablecoin_market_cap":stable_cap,"stablecoin_market_cap_change_24h_pct":stable_delta,"semantic":"market-cap change proxy; not literal net inflow"},
      "crowd":{"model":"v2-provisional","factors":factors,"coverage_pct":round(coverage),"derivative_factor_count":derivatives,"external_context_present":external,"quality_passed":quality,"score":score,"state":crowd_state,"action":action},
      "risk":{"status":"N/A","reason":"Risk Engine not historically validated"},
      "regime":{"status":"N/A","reason":"Transition history required"},
      "capital_flow":{"status":"WARMUP","shadow":True,"reason":"7D persistent history required"},
    }

def main():
    results={
      "cg":get_json(CG_GLOBAL),
      "stable":get_json(CG_STABLE),
      "ticker":get_json(GATE_TICKER),
      "stats":get_json(GATE_STATS),
    }
    snapshot=build(results)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"generated_at":snapshot["generated_at"],"sources":snapshot["source_status"],"coverage":snapshot["crowd"]["coverage_pct"],"quality":snapshot["crowd"]["quality_passed"],"score":snapshot["crowd"]["score"],"state":snapshot["crowd"]["state"]},ensure_ascii=False))

if __name__=="__main__":
    main()
