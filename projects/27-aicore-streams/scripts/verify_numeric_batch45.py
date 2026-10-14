import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
exe='research/batch45/numeric-validation-ubsan.exe';start=time.perf_counter();runs=[];total=0
for label in ['numeric-controls','numeric-parallel','numeric-parallel-valid','scaled-serial-controls']:
    data=f'data/{label}-batch42.json';out=f'reports/{label}-validation-ubsan-batch45.json';cmd=[exe,data,out]
    # The first driver already returned0 before the orchestration read an
    # incorrect field name("match" instead of actual "pass"). Do not rerun it.
    reuse=label=='numeric-controls' and Path(out).exists()
    if reuse:
        stdout=Path(out.replace('.json','.txt')).read_text();assert '11/11 fixed-plan bigint gold checks' in stdout and 'runtime error:' not in stdout;code=0
    else:
        r=subprocess.run(cmd,capture_output=True,text=True);stdout=r.stdout+r.stderr;code=r.returncode
        Path(out.replace('.json','.txt')).write_text(stdout,encoding='utf-8');assert code==0 and 'runtime error:' not in stdout
    doc=json.loads(Path(out).read_text());rows=doc['cases'];assert all(x['pass'] for x in rows);total+=len(rows)
    runs.append(dict(suite=label,actual_exit_code=code,controls=len(rows),reuse_same_successful_driver_after_wrapper_schema_repair=reuse,input_sha=sha(data),output_sha=sha(out),log_sha=sha(out.replace('.json','.txt'))));print(label,len(rows),stdout.strip())
assert total==523
report=dict(status='passed',fixed_plan_controls=total,source_sha=sha('research/batch45/solution.cpp'),exe_sha=sha(exe),runs=runs,shared_functional_wall_seconds=time.perf_counter()-start,UBSan_runtime_errors=0,compiler='Clang21.1 -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined',link_warnings='UCRT LNK4217 recorded separately, no runtime UB',workspace_gold=495,workspace_UBSan_evidence='reports/projection-profile-ubsan-batch45.txt (same frozen5116 source, actual earlier execution, not repeated)',default44_preserved=sha('solution/solution.cpp'))
Path('reports/full-numeric-verification-batch45.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(total,'candidate45 UBSan fixed-plan controls passed')
