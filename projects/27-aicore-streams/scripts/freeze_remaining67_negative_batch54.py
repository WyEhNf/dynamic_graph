"""Freeze all actual67 outcomes and unchanged source/default; no new solve."""
from pathlib import Path
import hashlib,json
P=Path('research/batch54');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
plan=json.loads((P/'functional-plan.json').read_text());complete=json.loads((P/'completion.json').read_text());status=json.loads((P/'execution-status.json').read_text());summary=json.loads(Path('reports/final-live-remaining67-summary-batch54.json').read_text());raw=json.loads(Path('reports/final-live-remaining67-batch54.json').read_text())['cases']
paths=set()
for m in (plan,complete):
    for f in m['files']:assert sha(f['path'])==f['sha256'],f['path'];paths.add(f['path'])
assert status['actual_exit_code']==status['verifier_actual_exit_code']==0
assert summary['before_legal']==summary['after_legal']==4 and not summary['restored'] and not summary['lost'] and not summary['common_quality_changes']
assert all(r['whole_plan_equal'] for r in summary['comparisons'])
assert sha('solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
assert sha('reports/project27-research.tex')=='e6e735ff65657d4d5cb7fb5ae6321edada13a0d1972932239da35c885e40ed82'
paths.update(['research/batch54/functional-plan.json','research/batch54/completion.json','reports/research-batch54.md','scripts/freeze_remaining67_negative_batch54.py'])
out=dict(status='ACTUAL_SINGLE67_NEGATIVE_RESULT_FROZEN_NOT_PROMOTED',records=67,remaining_known_feasible_failed=63,old_restored_controls=4,whole_legal=4,helper_legal=sum(c['helper']['valid'] for c in raw),helper_exhausted=sum(c['helper']['exhausted'] for c in raw),new_whole_recoveries=0,lost=0,common_whole_plans_T_peak_equal=True,logical_work=summary['logical_work'],thread_cpu_or_paired_speed_unmeasured=True,shared_functional_driver_wall_seconds=status['shared_functional_wall_seconds'],candidate_source_sha256=sha('research/batch53/solution.cpp'),candidate_exe_sha256=sha('research/batch53/selected12-gcc.exe'),default_batch=51,default_source_unchanged=True,old_open_tex_unchanged=True,compile_or_full250_1099_or_performance_executed=False,all_failure_records_preserved=True,files=[dict(path=f,sha256=sha(f)) for f in sorted(paths)])
(P/'negative-checkpoint.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(path=str(P/'negative-checkpoint.json'),sha256=sha(P/'negative-checkpoint.json'),frozen_files=len(paths)),indent=2))
