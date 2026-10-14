"""Fresh exact-source Clang523 fixed plans +495 profile +83/210 groupgold."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
start=time.perf_counter();runs=[];total=0
for label in ('numeric-controls','numeric-parallel','numeric-parallel-valid','scaled-serial-controls'):
    data=f'data/{label}-batch42.json';out=f'reports/{label}-validation-ubsan-batch48.json';cmd=['research/batch48/numeric-validation-ubsan.exe',data,out];r=subprocess.run(cmd,capture_output=True,text=True);stdout=r.stdout+r.stderr;Path(out.replace('.json','.txt')).write_text(stdout,encoding='utf-8');assert r.returncode==0 and 'runtime error:' not in stdout
    rows=json.loads(Path(out).read_text())['cases'];assert all(x['pass'] for x in rows);total+=len(rows);runs.append(dict(label=label,actual_exit_code=r.returncode,controls=len(rows),input_sha=sha(data),output_sha=sha(out),log_sha=sha(out.replace('.json','.txt'))));print(label,len(rows),'actualexit0',flush=True)
assert total==523
for label,data in [('projection','data/projection-gold-batch45.json'),('group','data/group-gold-batch48.json')]:
    cmd=[f'research/batch48/{label}-validation-ubsan.exe',data];r=subprocess.run(cmd,capture_output=True,text=True);stdout=r.stdout+r.stderr;log=f'reports/{label}-profile-ubsan-batch48.txt';Path(log).write_text(stdout,encoding='utf-8');assert r.returncode==0 and 'runtime error:' not in stdout;runs.append(dict(label=label,actual_exit_code=r.returncode,input_sha=sha(data),log_sha=sha(log),output=stdout.strip()));print(stdout.strip(),flush=True)
report=dict(status='passed',source_sha=sha('research/batch48/solution.cpp'),fixed_plan_controls=523,workspace_profiles=495,group_recognition_controls=83,group_moved_profiles=210,runs=runs,UBSan_runtime_errors=0,exe_sha={x:sha(f'research/batch48/{x}-validation-ubsan.exe') for x in ('numeric','projection','group')},compiler='Clang21.1 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined',link_warnings='UCRT LNK4217 logged separately from runtime UB',shared_functional_wall_seconds=time.perf_counter()-start,default45_preserved=sha('solution/solution.cpp'))
Path('reports/full-numeric-verification-batch48.json').write_text(json.dumps(report,indent=2));print('R48 fresh independent arithmetic/profile/group UBsan passed',flush=True)
