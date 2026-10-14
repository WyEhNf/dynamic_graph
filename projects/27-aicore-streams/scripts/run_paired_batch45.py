"""Only run AFTER an explicit coordinated root performance window."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch45');plan=json.loads((p/'paired-plan.json').read_text());source=str(p/'solution.cpp');before=plan['baseline_exe_path'];after=plan['candidate_exe_path']
assert sha(source)==plan['candidate_source'] and sha(before)==plan['baseline_exe'] and sha(after)==plan['candidate_exe']
started=time.perf_counter()
for label,data in [('hard','data/hard-corpus-resumed.json'),('heldout','data/projection-retention-heldout-batch45.json')]:
    assert sha(data)==plan['datasets'][data]
    subprocess.run(['C:/Users/admin/miniconda3/python.exe','scripts/paired_benchmark.py','--baseline',before,'--current',after,'--current-source',source,'--suite',data,'--prefix',f'reports/paired-{label}-batch45','--repetitions','3','--allow-after-failures'],check=True)
assert sha(source)==plan['candidate_source'] and sha(before)==plan['baseline_exe'] and sha(after)==plan['candidate_exe']
print('Actual R45 pairs complete shared CLI wall',time.perf_counter()-started,flush=True)
