"""New exact-source Clang523 fixed+102cut fixed/probes+495+83/210."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
start=time.perf_counter();runs=[];total=0
for label,data in [(x,f'data/{x}-batch42.json') for x in ('numeric-controls','numeric-parallel','numeric-parallel-valid','scaled-serial-controls')]+[('release-cut-fixed','data/release-cut-fixed-gold-batch51.json')]:
    out=f'reports/{label}-validation-ubsan-batch51.json';cmd=['research/batch51/numeric-validation-ubsan.exe',data,out];r=subprocess.run(cmd,capture_output=True,text=True);stdout=r.stdout+r.stderr;Path(out.replace('.json','.txt')).write_text(stdout,encoding='utf-8');assert r.returncode==0 and 'runtime error:' not in stdout
    rows=json.loads(Path(out).read_text())['cases'];assert all(x['pass'] for x in rows);total+=len(rows);runs.append(dict(label=label,actual_exit_code=r.returncode,controls=len(rows),input_sha=sha(data),output_sha=sha(out),log_sha=sha(out.replace('.json','.txt'))));print(label,len(rows),'actualexit0',flush=True)
assert total==625
for label,data in [('projection','data/projection-gold-batch45.json'),('group','data/group-gold-batch48.json'),('cut','data/release-cut-gold-batch51.json')]:
    cmd=[f'research/batch51/{label}-validation-ubsan.exe',data];r=subprocess.run(cmd,capture_output=True,text=True);stdout=r.stdout+r.stderr;log=f'reports/{label}-profile-ubsan-batch51.txt';Path(log).write_text(stdout,encoding='utf-8');assert r.returncode==0 and 'runtime error:' not in stdout;runs.append(dict(label=label,actual_exit_code=r.returncode,input_sha=sha(data),log_sha=sha(log),output=stdout.strip()));print(stdout.strip(),flush=True)
report=dict(status='passed',source_sha=sha('research/batch51/solution.cpp'),existing_fixed_plan_controls=523,new_complete_cut_fixed_plans=102,new_cut_probes=102,workspace_profiles=495,group_recognition_controls=83,group_moved_profiles=210,runs=runs,UBSan_runtime_errors=0,exe_sha={x:sha(f'research/batch51/{x}-validation-ubsan.exe') for x in ('numeric','projection','group','cut')},compiler='Clang21.1 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined',link_warnings='Any UCRT LNK4217 logged separately from runtime UB',shared_functional_wall_seconds=time.perf_counter()-start,default48_preserved=sha('solution/solution.cpp'))
Path('reports/full-numeric-verification-batch51.json').write_text(json.dumps(report,indent=2));print('R51 fresh independent arithmetic/profile/group/cut UBSan passed',flush=True)
