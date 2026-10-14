"""Freeze one actual authorized terminal; does not initiate or repeat trials."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--actual-session', type=int, required=True)
parser.add_argument('--actual-exit-code', type=int, required=True)
args = parser.parse_args()
assert args.actual_exit_code == 0
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
p = Path('research/batch51')
plan = json.loads((p/'paired-plan.json').read_text(encoding='utf-8'))
driver = json.loads((p/'paired-driver-status.json').read_text(encoding='utf-8'))
cost = json.loads(Path('reports/resource-cost-summary-batch51.json').read_text(encoding='utf-8'))
assert driver['plan_sha'] == sha(p/'paired-plan.json')
assert len(driver['statuses']) == 2 and all(row['actual_exit_code'] == 0 for row in driver['statuses'])
assert cost['hard']['counts'] == dict(all=202, common_success=144, common_failure=57, recovered=1)
assert cost['heldout']['counts'] == dict(all=48, common_success=42, common_failure=6, recovered=0)
for report in cost.values():
    assert report['source_sha'] == plan['candidate_source']
    assert report['exe_sha'] == plan['candidate_exe']
    assert report['baseline_exe_sha'] == plan['baseline_exe']
for path, expected in plan['scripts'].items():
    assert sha(path) == expected
assert sha('solution/solution.cpp') == plan['default_unchanged_sha']
assert sha('build/aicore_bench.exe') == plan['default_exe_unchanged_sha']
assert sha('reports/project27-research.tex') == plan['old_tex_unchanged_sha']
files = list(plan['scripts']) + [
    'research/batch51/paired-plan.json', 'research/batch51/paired-driver-status.json',
    'research/batch51/acceptance-checkpoint.json', 'scripts/summarize_cost_batch51.py',
    'scripts/summarize_cost_batch45.py', 'scripts/freeze_paired_completion_batch51.py',
    'reports/resource-cost-summary-batch51.json']
for family in ('hard', 'heldout'):
    files += [f'reports/paired-{family}-batch51-summary.json',
              f'reports/resource-cost-{family}-batch51.json',
              f'reports/paired-{family}-driver-batch51.txt']
    for n in range(1,4):
        for side in ('before', 'after'):
            base = f'reports/paired-{family}-batch51-{n}-{side}'
            files += [base+suffix for suffix in (
                '.json', '.csv', '.failures.json', '.host.json', '.stdout.txt', '.stderr.txt')]
manifest = dict(
    status='Single authorized R51 paired batch actual terminal;default48 unchanged;promotion pending root review',
    actual_session=args.actual_session, actual_exit_code=args.actual_exit_code,
    full_driver_wall_seconds=driver['actual_wall_seconds'],
    trials=12, case_execution_records=1500,
    source_sha=sha(plan['candidate_source_path']),
    candidate_exe_path=plan['candidate_exe_path'], candidate_exe_sha=sha(plan['candidate_exe_path']),
    baseline_exe_path=plan['baseline_exe_path'], baseline_exe_sha=sha(plan['baseline_exe_path']),
    files={path: sha(path) for path in files}, cost=cost,
    host_observation='Pertrial endpoints/0.25s CPU ticks+available physical RAM;raw/API errors preserved;sampled, includes user background;not OS-isolated',
    no_extra_runs=True, no_harness_change_during_run=True,
    default48_source_sha=sha('solution/solution.cpp'),
    default48_exe_sha=sha('build/aicore_bench.exe'),
    old_open_tex_sha=sha('reports/project27-research.tex'))
(p/'paired-completion.json').write_text(json.dumps(manifest,indent=2)+'\n', encoding='utf-8')
print('Actual paired completion frozen', sha(p/'paired-completion.json'), flush=True)
