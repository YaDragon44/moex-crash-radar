from moex_crash_radar.dashboard_contract import validate_dashboard_snapshot

def good_snapshot():
    signals={k:{"score":50.0,"quality":"LIVE"} for k in ("market_structure","breadth","volume_distribution","volatility_liquidity","levels_momentum")}
    signals["rate_ofz"]={"score":52.0,"quality":"LIVE"}; signals["oil_rub"]={"score":61.0,"quality":"LIVE"}
    return {"release":"R0.5.2 Oil / RUB Live Integration","as_of":"2026-08-28T09:45:00+03:00","source":"MOEX ISS","secid":"IMOEX","last_close":2087.96,"data_quality":"LIVE","signals":signals,
      "context":{"score":55.75,"state":"CAUTION","quality":"LIVE","coverage":.60,"available_groups":2,"total_groups":4,"groups":{
        "rate_ofz":{"score":52.0,"quality":"LIVE","key_rate":14.0,"key_rate_day":"2026-08-27","median_long_ofz_yield":14.8,"ofz_count":18,"rgbi_return_5d":-.5,"rgbi_return_20d":-1.2,"component_coverage":1.0,"sources":["Bank of Russia","MOEX ISS TQOB","MOEX ISS RGBI"]},
        "oil_rub":{"score":61.0,"quality":"LIVE","brent_secid":"BR-9.26","brent_return_5d":-3.2,"brent_return_20d":-8.1,"cnyrub_return_5d":2.1,"cnyrub_return_20d":6.4,"component_coverage":1.0,"latest_day":"2026-08-28","sources":["MOEX ISS FORTS Brent","MOEX ISS CNYRUB_TOM"]},
        "macro_earnings":{"score":None,"quality":"N/A"},"news_geopolitics":{"score":None,"quality":"N/A"}}},
      "crash":{"score":55.94,"available_weight":.72,"critical_confirmations":1},"crash_history":[{"day":"2026-08-27","score":53.0,"state":"DEFENSIVE"},{"day":"2026-08-28","score":55.94,"state":"DEFENSIVE"}],
      "exit_gate":{"stage":"EARLY_WARNING","cash_confirmed":False,"params":{"score_threshold":65.0,"early_warning_threshold":56.0,"confirmations":3,"persistence":2,"max_5d_return_pct":-3.0,"cooldown_rows":30,"require_breadth_volume":False,"rearm_clear_rows":3}},
      "bottom":{"score":None,"state":"DATA_INSUFFICIENT","buy_back_signal":False},"calibration":{"release":"R0.3.3","false_event_rate":.2857,"detected_episodes":"4/4","median_lead_days":28.5,"total_exit_events":14,"false_exit_events":4},"note":"Live MOEX market layer is active."}

def test_valid_dashboard_contract_passes(): assert validate_dashboard_snapshot(good_snapshot())==[]
def test_missing_core_signal_fails():
    s=good_snapshot(); del s["signals"]["breadth"]; assert any("breadth" in e for e in validate_dashboard_snapshot(s))
def test_rate_sources_required():
    s=good_snapshot(); s["context"]["groups"]["rate_ofz"]["sources"]=["unknown"]; assert any("official CBR and MOEX" in e for e in validate_dashboard_snapshot(s))
def test_oil_sources_required():
    s=good_snapshot(); s["context"]["groups"]["oil_rub"]["sources"]=["unknown"]; assert any("MOEX Brent and CNYRUB" in e for e in validate_dashboard_snapshot(s))
def test_oil_component_coverage_required():
    s=good_snapshot(); s["context"]["groups"]["oil_rub"]["component_coverage"]=.5; assert any("oil_rub component_coverage" in e for e in validate_dashboard_snapshot(s))
def test_oil_signal_must_match_group():
    s=good_snapshot(); s["signals"]["oil_rub"]["score"]=99; assert any("signals.oil_rub" in e for e in validate_dashboard_snapshot(s))
def test_context_needs_two_groups():
    s=good_snapshot(); s["context"]["available_groups"]=1; assert any(">=2 groups" in e for e in validate_dashboard_snapshot(s))
def test_unsourced_macro_cannot_be_fabricated():
    s=good_snapshot(); s["context"]["groups"]["macro_earnings"]={"score":42,"quality":"LIVE"}; assert any("macro_earnings" in e for e in validate_dashboard_snapshot(s))
def test_cash_stage_requires_confirmation():
    s=good_snapshot(); s["exit_gate"]["stage"]="CASH_CONFIRMED"; assert any("cash_confirmed=true" in e for e in validate_dashboard_snapshot(s))
def test_synthetic_marker_rejected():
    s=good_snapshot(); s["note"]="synthetic fallback"; assert any("synthetic" in e for e in validate_dashboard_snapshot(s))
def test_crash_history_required():
    s=good_snapshot(); del s["crash_history"]; assert any("crash_history" in e for e in validate_dashboard_snapshot(s))

def test_dashboard_html_has_r052_hooks():
    html=open("web/r044.html",encoding="utf-8").read()
    for token in ("market_snapshot.json","R0.5.2","MARKET","ТОЛПА","РИСК","РЕЖИМ","ПЕРЕХОД","ДЕЙСТВИЕ","Ставка / ОФЗ","Нефть / RUB","Brent","CNYRUB","contextState","Начало СВО","COVID","q!=='LIVE'","DELAYED"):
        assert token in html
    assert "@media(max-width:1200px)" in html and "@media(max-width:700px)" in html

def test_dashboard_keeps_crowd_na():
    html=open("web/r044.html",encoding="utf-8").read(); assert "Crowd Engine ещё не подключён" in html and "crowdState').textContent='N/A" in html

def test_context_does_not_override_calibrated_exit():
    html=open("web/r044.html",encoding="utf-8").read(); assert "не меняет calibrated EXIT Gate" in html and "самостоятельным CASH-сигналом" in html
