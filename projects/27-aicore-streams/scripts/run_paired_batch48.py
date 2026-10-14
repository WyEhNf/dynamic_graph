"""Only after explicit second-stage root performance authorization."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch48');plan=json.loads((p/'paired-plan.json').read_text());before=plan['baseline_exe_path'];after=plan['candidate_exe_path'];source=str(p/'solution.cpp');assert sha(source)==plan['candidate_source'] and sha(before)==plan['baseline_exe'] and sha(after)==plan['candidate_exe']
started=time.perf_counter()
for label,data in [('hard','data/hard-corpus-resumed.json'),('heldout','data/projection-retention-heldout-batch45.json')]:
    assert sha(data)==plan['datasets'][data]
    with Path(f'reports/paired-{label}-driver-batch48.txt').open('w',encoding='utf-8') as f:subprocess.run(['C:/Users/admin/miniconda3/python.exe','scripts/paired_benchmark.py','--baseline',before,'--current',after,'--current-source',source,'--suite',data,'--prefix',f'reports/paired-{label}-batch48','--repetitions','3','--allow-after-failures'],stdout=f,stderr=subprocess.STDOUT,check=True)
    print(label,'actual three-round terminal',flush=True)
assert sha(source)==plan['candidate_source'] and sha(before)==plan['baseline_exe'] and sha(after)==plan['candidate_exe']
print('Actual batch48 paired full CLI wall',time.perf_counter()-started,flush=True)
