"""Authorized <=12 original-case observer functionality; no performance/branch."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
p=Path('research/batch52');plan=json.loads((p/'observer-plan.json').read_text())
for path,expected in plan['paths'].items():assert sha(path)==expected,path
assert sha('solution/solution.cpp')==plan['default_source_sha'] and sha('build/aicore_bench.exe')==plan['default_exe_sha']
temp=(p/'compiler-temp').resolve();temp.mkdir(exist_ok=True)
env=os.environ.copy()
for name in ('TEMP','TMP','TMPDIR'):env[name]=str(temp)
started=time.perf_counter();statuses=[]
def run(label,command,allowed=(0,)):
    before=time.perf_counter();result=subprocess.run(command,capture_output=True,text=True,env=env)
    Path(f'reports/observer-{label}-batch52.stdout.txt').write_text(result.stdout,encoding='utf-8')
    Path(f'reports/observer-{label}-batch52.stderr.txt').write_text(result.stderr,encoding='utf-8')
    statuses.append(dict(label=label,command=command,actual_exit_code=result.returncode,shared_functional_wall_seconds=time.perf_counter()-before))
    (p/'observer-status.json').write_text(json.dumps(dict(plan_sha=sha(p/'observer-plan.json'),statuses=statuses,process_environment_overrides={name:env[name] for name in ('TEMP','TMP','TMPDIR')},system_environment_modified=False,shared_functional_wall_seconds=time.perf_counter()-started),indent=2)+'\n',encoding='utf-8')
    print(label,'actual exit',result.returncode,flush=True);assert result.returncode in allowed,label
for role in ('baseline','observed'):
    command=['E:/mingw64/bin/g++.exe','-O2','-std=c++17','-Iinclude','research/batch52/observer-driver.cpp','src/simulator.cpp','-o',f'research/batch52/{role}-driver.exe']
    if role=='observed':command.insert(1,'-DR52_OBSERVER')
    run('build-'+role,command)
for role in ('baseline','observed'):
    run(role,[f'research/batch52/{role}-driver.exe','research/batch52/observer-selected12-input-only.json',f'reports/observer-{role}-batch52.json'])
run('actual-default',['build/aicore_bench.exe','--input','research/batch52/observer-selected12-input-only.json','--output','reports/observer-actual-default-batch52.json'],allowed=(1,))
run('whole-python-gold',['C:/Users/admin/miniconda3/python.exe','scripts/make_whole_gold_batch52.py'])
run('whole-numeric-gold',['research/batch51/numeric-validation-ubsan.exe','research/batch52/whole-fixed-gold.json','reports/whole-numeric-gold-batch52.json'])
run('verify',['C:/Users/admin/miniconda3/python.exe','scripts/verify_observer_batch52.py'])
for path,expected in plan['paths'].items():assert sha(path)==expected,path
assert sha('research/batch51/provenance.json')==plan['default_provenance_sha']
assert sha('reports/project27-research.tex')==plan['old_tex_sha']
print('Small observer diagnostic terminal;default51 unchanged;no branch/performance',flush=True)
