"""Record final evidence provenance without running or modifying the solver."""
import hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'isa_scheduler').glob('*.py'))}
aggregate=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
folder=ROOT/'experiments/milestone-v14'
report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
assert {k.replace('\\','/'):v for k,v in report['current_source_manifest_at_start'].items()}==manifest
for source in ('r80-terminal-default','milestone-v13'):
 earlier=json.loads((ROOT/'experiments'/source/'report.json').read_text(encoding='utf-8'))
 assert {k.replace('\\','/'):v for k,v in earlier['current_source_manifest_at_start'].items()}==manifest
fuzz=json.loads((folder/'fuzz.json').read_text(encoding='utf-8'))
provenance={'frozen_utc':'2026-10-10T21:10:32.780194+00:00','evidence_audited_utc':datetime.now(timezone.utc).isoformat(),'core_manifest':manifest,'core_aggregate_sha256':aggregate,
 'default_parameters':{'strategy':'auto','time_budget_ms':100,'max_states':30000,'beam_width':128,'memory_order':'hazard','bound_tolerance':0.005,'bound_tolerance_scope':'explicit bound_portfolio only; auto terminal optimality stop tolerance is zero'},
 'tests':{'count':133,'elapsed_seconds':49.249,'execution_source':'experiments/r80-terminal-default/tests-complete.log','copied_log':'tests.log'},
 'fuzz':{'cases':10000,'verified':fuzz['verified_cases_auto'],'elapsed_seconds':fuzz['elapsed_seconds'],'execution_source':'experiments/milestone-v13/fuzz.json','copied_report':'fuzz.json'},
 'reuse_reason':'No core module changed between passed tests/fuzz and v14 benchmark. Only research harness missing-old-witness accounting was repaired. Counts refer to actual execution source, not repeated execution.',
 'invalid_previous_benchmark':'milestone-v13 report preserved: missing old original_order caused harness KeyError after symbolic verification but before integer checks. Its old status counts are invalid; replaced by fresh v14 run, not edited.',
 'old_identity_scope':'Old baseline lacks original_order; no exact identity proof claimed or reconstructed. Valid v14 outputs retain symbolic plus three integer checks.',
 'report_sha256':hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),
 'artifact_sha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest()for name in ('tests.log','fuzz.json','inputs.jsonl','optimized_outputs.jsonl','original_orders.jsonl','records.csv')}}
(folder/'validation-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ('milestone-v14','r78-bound-identity-online','r80-terminal-default','r81-terminal-default-holdout'):
 r=json.loads((ROOT/'experiments'/name/'report.json').read_text(encoding='utf-8'))
 print(json.dumps({'round':name,'elapsed_seconds':r['elapsed_seconds'],'identity_status_counts':dict(Counter(x.get('identity_check_status','missing')for x in r['records']if x['status']=='verified'))}))
print(json.dumps({'core_aggregate_sha256':aggregate,'freeze_utc':provenance['frozen_utc'],'disk_bytes':sum(p.stat().st_size for p in ROOT.rglob('*')if p.is_file())}))
