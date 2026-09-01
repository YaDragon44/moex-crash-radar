from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

from scripts.btc_entry_radar_r1_4_0 import EntryRadarInput, to_dict


def parse_bool(v: str):
    if v.lower() in {"true","1","yes","y"}: return True
    if v.lower() in {"false","0","no","n"}: return False
    if v.lower() in {"na","n/a","none","null"}: return None
    raise argparse.ArgumentTypeError("expected true/false/n/a")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fgi", type=float, required=True)
    p.add_argument("--btc-price", type=float, required=True)
    p.add_argument("--price-confirm-4h", type=parse_bool, default=None)
    p.add_argument("--new-local-low-4h", type=parse_bool, default=None)
    p.add_argument("--oi-regime", default="N/A")
    p.add_argument("--stop-atr", type=float, default=None)
    p.add_argument("--quality-coverage", type=float, default=50.0)
    p.add_argument("--data-ready", action="store_true")
    p.add_argument("--source-note", default="manual verified live snapshot")
    args=p.parse_args()

    radar=EntryRadarInput(
        fgi=args.fgi,
        price_confirm_4h=args.price_confirm_4h,
        new_local_low_4h=args.new_local_low_4h,
        oi_regime=args.oi_regime,
        stop_atr=args.stop_atr,
        data_ready=args.data_ready,
    )
    out=to_dict(radar)
    out["market"]={"btc_price_usd":args.btc_price}
    out["quality"]={
        "coverage_pct":args.quality_coverage,
        "status":"DATA READY" if args.data_ready else "PARTIAL",
        "source_note":args.source_note,
    }
    out["generated_at_utc"]=datetime.now(timezone.utc).isoformat()
    target=Path("artifacts/btc_entry_radar_live_snapshot.json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(out,indent=2))

if __name__=="__main__": main()
