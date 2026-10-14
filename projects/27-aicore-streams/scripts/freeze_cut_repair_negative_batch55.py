"""Freeze actual R55 evidence; no compiler, solver, or mutation of prior data."""
from pathlib import Path
import hashlib,json
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=Path('research/batch55')
files=sorted([p for p in base.rglob('*') if p.is_file() and 'compiler-temp' not in p.parts and p.name!='negative-checkpoint.json']+
             [p for p in Path('reports').glob('cut-repair-*batch55*') if p.is_file()]+
             [p for p in Path('scripts').glob('*batch55.py') if p.is_file()])
summary=json.loads(Path('reports/cut-repair-selected12-summary-batch55.json').read_text())
assert summary['whole_recovered']==summary['whole_lost']==0
assert summary['before_whole_success']==summary['after_whole_success']==4
assert all(r['common_whole_plan_equal'] for r in summary['rows'] if r['before_whole_valid'])
out=dict(status='NEGATIVE_ACTUAL_TERMINAL_NO_PROMOTION',scope='160 gold plus original R52 twelve only; not all63',
 actual_gold_exit=0,actual_selected12_exit=0,selected12_owner_pid=95044,live_handles=[],
 before_success=4,after_success=4,remaining_failures=8,recoveries=0,lost=0,common_plans_T_peak_equal=True,
 logical_work_before=54717560,logical_work_after=60829525,logical_work_delta=6111965,
 performance_unmeasured=True,default_unchanged=True,stop_expansion=True,
 limitations='Width2/branch2 cannot prove infeasibility. Repair only changes the order within one original closure; complete closure final live/remaining-user state is fixed by its completed set. No claims for unobserved original63.',
 files=[dict(path=p.as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in files],
 preserved=[dict(path=str(p),sha256=sha(p)) for p in map(Path,['solution/solution.cpp','build/aicore_bench.exe','reports/project27-research.tex'])])
(base/'negative-checkpoint.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(files),checkpoint_sha256=sha(base/'negative-checkpoint.json'))))
