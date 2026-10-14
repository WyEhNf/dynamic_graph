"""Record actual single authorized terminal, no measurements are repeated."""
import hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch48');cost=json.loads(Path('reports/resource-cost-summary-batch48.json').read_text());plan=json.loads((p/'paired-plan.json').read_text())
assert cost['hard']['counts']==dict(all=202,common_success=143,common_failure=58,recovered=1)
assert cost['heldout']['counts']==dict(all=48,common_success=42,common_failure=6,recovered=0)
assert all(r['source_sha']==plan['candidate_source'] and r['exe_sha']==plan['candidate_exe'] and r['baseline_exe_sha']==plan['baseline_exe'] for r in cost.values())
files=['research/batch48/paired-plan.json','research/batch48/acceptance-checkpoint.json','scripts/run_paired_batch48.py','scripts/paired_benchmark.py','scripts/summarize_cost_batch48.py','scripts/summarize_cost_batch45.py','reports/resource-cost-summary-batch48.json']
files += [f'reports/paired-{family}-batch48-{n}-{side}.json' for family in ('hard','heldout') for n in range(1,4) for side in ('before','after')]
files += [f'reports/paired-{family}-batch48-summary.json' for family in ('hard','heldout')]
manifest=dict(status='single authorized R48 paired batch terminal;default45 unchanged',actual_session=65788,actual_exit_code=0,full_cli_wall_seconds=185.29292149998946,source_sha=sha(p/'solution.cpp'),candidate_exe_sha=sha(plan['candidate_exe_path']),baseline_exe_sha=sha(plan['baseline_exe_path']),files={x:sha(x) for x in files},cost=cost,no_extra_runs=True,hostbusy_availableRAM='unmeasured',default45_source_sha=sha('solution/solution.cpp'),default45_exe_sha=sha('build/aicore_bench.exe'))
(p/'paired-completion.json').write_text(json.dumps(manifest,indent=2));print(sha(p/'paired-completion.json'),flush=True)
