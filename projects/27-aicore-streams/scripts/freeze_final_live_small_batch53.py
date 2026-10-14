"""Freeze actual initial failure, corrected gate and unchanged default together."""
from pathlib import Path
import hashlib,json
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
P=Path('research/batch53')
initial_plan=json.loads((P/'execution-plan.json').read_text());initial=json.loads((P/'completion.json').read_text())
revised_map=json.loads((P/'corrected/revision-map.json').read_text());revised=json.loads((P/'corrected/completion.json').read_text())
paths=set()
for manifest in (initial_plan,initial,revised):
    for f in manifest['files']:assert sha(f['path'])==f['sha256'],f['path'];paths.add(f['path'])
for f in revised_map['frozen_files']:assert sha(f['path'])==f['sha256'],f['path'];paths.add(f['path'])
assert all(s['actual_exit_code']==0 for s in initial['statuses']+revised['statuses'])
assert sha('solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
assert sha('reports/project27-research.tex')=='e6e735ff65657d4d5cb7fb5ae6321edada13a0d1972932239da35c885e40ed82'
paths.update(str(f).replace('\\','/') for f in Path('reports').glob('final-live-*-batch53.*.txt'))
paths.update(['reports/research-batch53.md','research/batch53/completion.json','research/batch53/execution-status.json','research/batch53/corrected/completion.json','research/batch53/corrected/execution-status.json','scripts/freeze_final_live_small_batch53.py','scripts/prepare_final_live_batch53.py','research/batch53/static-freeze.json','reports/research-batch53-design.md'])
summary=json.loads(Path('reports/final-live-corrected-summary-batch53.json').read_text())
out=dict(status='SMALL_ACCEPTANCE_CORRECTED_COMPLETE_NOT_PROMOTED',candidate_source_sha256=sha(P/'solution.cpp'),default_batch=51,default_unchanged=True,old_open_tex_unchanged=True,initial_qualification_failed=7,initial_physical_numeric_checks_passed=True,initial_all_logs_and_inputs_preserved=True,corrected_controls=176,corrected_random_qualified=64,corrected_original_cut_orders=558,actual_corrected_compilers=['GCC15.2-O2','Clang21.1-O1-UBSan'],probe_requests_each=347,charged_budget_controls=32,whole_fixed_physical_cases=347,expected_legal=311,expected_invalid=36,selected12_original_actual_run_reused=True,selected12_success_before=4,selected12_success_after=4,new_restored=0,lost=0,whole_plans_and_helper_orders_equal=True,logical_work_cases=dict(increased=5,decreased=4,equal=3),performance_unmeasured=True,no_remaining63_full250_1099_or_defaultpromotion=True,files=[dict(path=f,sha256=sha(f)) for f in sorted(paths)])
(P/'small-acceptance-checkpoint.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(path=str(P/'small-acceptance-checkpoint.json'),sha256=sha(P/'small-acceptance-checkpoint.json'),frozen_files=len(paths),candidate_source_sha256=out['candidate_source_sha256']),indent=2))
