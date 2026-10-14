"""Prepare only: absolutely no subprocess/performance execution."""
import hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch45');m=json.loads((p/'acceptance-checkpoint.json').read_text())
before='research/batch44/default-aicore_bench.exe';after='research/batch45/release-candidate-frozen-aicore_bench.exe';source='research/batch45/solution.cpp'
assert m['source_sha']==sha(source) and m['baseline44_exe_sha']==sha(before) and m['executables'][after]==sha(after)
plan=dict(status='declared_not_executed_waiting_root_window_after19_phase2',baseline_source=sha('research/batch44/solution.cpp'),candidate_source=sha(source),baseline_exe_path=before,candidate_exe_path=after,baseline_exe=sha(before),candidate_exe=sha(after),acceptance_checkpoint_sha=sha(p/'acceptance-checkpoint.json'),compiler='GCC15.2 CMake Release -O3 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic both',datasets={x:sha(x) for x in ['data/hard-corpus-resumed.json','data/projection-retention-heldout-batch45.json']},rounds=3,order='before/after, after/before, before/after per dataset',scope='all202 and all48 including failures; common successes, common failures and recovered separate; per-pair ratios plus independent-side medians; full CLI wall/working set; prior36/72 no extra performance',background='Parent reported about1.32GiB free RAM and active user apps; do not claim empty host. Record actual window background separately.',default_unchanged_sha=sha('solution/solution.cpp'))
(p/'paired-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print('plan declared only',sha(p/'paired-plan.json'))
