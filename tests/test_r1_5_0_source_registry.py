import json

def test_source_registry_fail_closed():
 p=json.load(open('config/r1_5_0_source_registry.json'))
 f=p['sources']['MOEX_FUTOI']
 assert f['access']=='SUBSCRIPTION_AUTH_REQUIRED'
 assert f['event_time_field']=='MOMENT'
 assert f['available_time_field']=='SYSTIME'
 assert set(f['participant_groups'])=={'FIZ','YUR'}
 assert f['unauthenticated_quality']=='BLOCKED_AUTH'
 assert f['daily_public_substitution_allowed'] is False
 assert p['ablation_readiness']['M0_PRICE']=='READY_PUBLIC'
 assert p['ablation_readiness']['M2_PRICE_POSITIONING']=='BLOCKED_AUTH'
