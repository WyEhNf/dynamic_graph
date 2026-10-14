"""Saved R57 vs original R51 plans; no solver execution and no promotion."""
import json
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/Hackathon-stage2-artifacts/project27/r57-necessary-prefix')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=ROOT/'reports/observer-baseline-batch52.json'
assert sha(baseline)=='91272eb1a05f0ed0758b836a1f40feceeb1e3adb7fc4e9f8240788686252b350'
old={r['name']:r for r in json.loads(baseline.read_text())['cases']}
raw=OUT/'selected12.json';new=json.loads(raw.read_text())['cases']
assert len(new)==12 and {r['name'] for r in new}==set(old)
rows=[]
for r in new:
    b=old[r['name']];h=r['helper'];w=r['whole'];before=b['whole']
    assert 0<=h['work']<=2000000
    if before['valid']:
        assert w['valid'] and w['plan']==before['plan'] and w['T']==before['T'] and w['peak']==before['peak']
    rows.append({'name':r['name'],'before_whole_valid':before['valid'],'after_whole_valid':w['valid'],
        'recovered':not before['valid'] and w['valid'],'new_helper_valid':h['valid'],
        'new_helper_work':h['work'],'states':h['evaluations'],'necessary_bound_prunes':h['peak_lo'],
        'monitored_targets':h['peak_hi'],'budget_exhausted':h['exhausted']})
report={'records':rows,'all_original12_preserved':True,'before_whole_success':sum(r['before_whole_valid'] for r in rows),
    'after_whole_success':sum(r['after_whole_valid'] for r in rows),'recoveries':sum(r['recovered'] for r in rows),
    'pruned_producer_decisions':sum(r['necessary_bound_prunes'] for r in rows),'default_changed':False,
    'driver_metric_translation':'R57 helper evaluations=states, peak_lo=prunes, peak_hi=monitored targets; these fields are NOT memory peaks',
    'controls':json.loads((OUT/'controls-report.json').read_text()),
    'failure_semantics':'search unknown; branch8, top64 and node512 bounds are not global infeasibility certificates',
    'performance_measured':False,'sha256':{str(p):sha(p) for p in [raw,baseline,OUT/'selected-driver.exe',ROOT/'research/batch57/necessary_prefix_search.inc',Path(__file__)]}}
with (ROOT/'reports/necessary-prefix-candidate-r57-2026-10-12.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:report[k] for k in ['before_whole_success','after_whole_success','recoveries','pruned_producer_decisions']}))
