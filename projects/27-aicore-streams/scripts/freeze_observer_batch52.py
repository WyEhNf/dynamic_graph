"""Freeze actual small-diagnostic terminal and all observation raw evidence."""
import hashlib
import json
from pathlib import Path

sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
p=Path('research/batch52');plan=json.loads((p/'observer-plan.json').read_text());status=json.loads((p/'observer-status.json').read_text())
assert status['plan_sha']==sha(p/'observer-plan.json')
assert len(status['statuses'])==8
assert [r['actual_exit_code'] for r in status['statuses']]==[0,0,0,0,1,0,0,0]
for path,expected in plan['paths'].items():assert sha(path)==expected,path
assert sha('solution/solution.cpp')==plan['default_source_sha']
assert sha('build/aicore_bench.exe')==plan['default_exe_sha']
assert sha('research/batch51/provenance.json')==plan['default_provenance_sha']
assert sha('reports/project27-research.tex')==plan['old_tex_sha']
summary=json.loads(Path('reports/observer-summary-batch52.json').read_text())
files=list(plan['paths'])+['research/batch52/observer-plan.json','research/batch52/observer-status.json',
       'research/batch52/baseline-driver.exe','research/batch52/observed-driver.exe',
       'research/batch52/whole-fixed-gold.json','reports/observer-summary-batch52.json',
       'scripts/freeze_observer_batch52.py']+list(summary['files'])
files += [f'reports/observer-{row["label"]}-batch52.{kind}.txt' for row in status['statuses'] for kind in ('stdout','stderr')]
completion=dict(status='Authorized small source-only observer complete;no newalgorithm/default changes',
                actual_session=35073,actual_exit_code=0,plan_sha=sha(p/'observer-plan.json'),
                files={path:sha(path) for path in sorted(set(files))},summary=summary,
                shared_functional_wall_seconds=status['shared_functional_wall_seconds'],
                constraints='12 original cases only,8fail+4recoveries;no full63/250/performance or branch;all baseline semantic fields identical,observations notcharged',
                default_source_sha=sha('solution/solution.cpp'),default_exe_sha=sha('build/aicore_bench.exe'),
                default_provenance_sha=sha('research/batch51/provenance.json'),old_open_tex_sha=sha('reports/project27-research.tex'))
(p/'observer-completion.json').write_text(json.dumps(completion,indent=2)+'\n',encoding='utf-8')
print('Actual observer complete',sha(p/'observer-completion.json'),flush=True)
