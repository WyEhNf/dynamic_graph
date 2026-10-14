"""Start only after root explicitly authorizes the frozen unique performance window."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
p = Path('research/batch51')
plan = json.loads((p/'paired-plan.json').read_text(encoding='utf-8'))
before, after, source = (plan[key] for key in (
    'baseline_exe_path', 'candidate_exe_path', 'candidate_source_path'))
def check():
    for key, path in [('baseline_exe', before), ('candidate_exe', after),
                      ('candidate_source', source), ('baseline_source', plan['baseline_source_path']),
                      ('default_unchanged_sha', 'solution/solution.cpp'),
                      ('default_exe_unchanged_sha', 'build/aicore_bench.exe'),
                      ('old_tex_unchanged_sha', 'reports/project27-research.tex')]:
        assert sha(path) == plan[key], (key, path)
    for path, expected in plan['scripts'].items():
        assert sha(path) == expected, path
    for path, expected in plan['datasets'].items():
        assert sha(path) == expected, path
    assert sha(p/'acceptance-checkpoint.json') == plan['acceptance_checkpoint_sha']
check()
started = time.perf_counter()
statuses = []
for label, data in [('hard', 'data/hard-corpus-resumed.json'),
                    ('heldout', 'data/projection-retention-heldout-batch45.json')]:
    command = ['C:/Users/admin/miniconda3/python.exe', 'scripts/paired_benchmark_batch51.py',
               '--baseline', before, '--current', after, '--current-source', source,
               '--suite', data, '--prefix', f'reports/paired-{label}-batch51',
               '--repetitions', '3', '--allow-after-failures']
    with Path(f'reports/paired-{label}-driver-batch51.txt').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    statuses.append(dict(label=label, command=command, actual_exit_code=result.returncode))
    (p/'paired-driver-status.json').write_text(json.dumps(dict(
        plan_sha=sha(p/'paired-plan.json'), statuses=statuses,
        actual_wall_seconds=time.perf_counter()-started), indent=2)+'\n', encoding='utf-8')
    assert result.returncode == 0, (label, result.returncode)
    print(label, 'actual three-round terminal', flush=True)
check()
print('Actual batch51 paired full CLI wall', time.perf_counter()-started, flush=True)
