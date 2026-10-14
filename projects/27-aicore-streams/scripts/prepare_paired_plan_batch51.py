"""Freeze declaration only. Does not start a benchmark or modify any default."""
import hashlib
import json
from pathlib import Path

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
p = Path('research/batch51')
acceptance = json.loads((p/'acceptance-checkpoint.json').read_text(encoding='utf-8'))
before = 'research/batch48/default-aicore_bench.exe'
after = 'research/batch51/release-candidate-frozen-aicore_bench.exe'
source = 'research/batch51/solution.cpp'
assert acceptance['source_sha'] == sha(source)
assert acceptance['default48_exe_sha'] == sha(before)
assert acceptance['executables'][after] == sha(after)
assert sha('solution/solution.cpp') == acceptance['default48_source_sha']
assert sha('build/aicore_bench.exe') == sha(before)
assert sha('reports/project27-research.tex') == acceptance['old_user_open_tex_sha']
plan = dict(
    status='declared_not_executed_waiting_explicit_unique_root_window',
    baseline_source_path='research/batch48/solution.cpp',
    baseline_source=sha('research/batch48/solution.cpp'),
    candidate_source_path=source, candidate_source=sha(source),
    baseline_exe_path=before, candidate_exe_path=after,
    baseline_exe=sha(before), candidate_exe=sha(after),
    baseline_provenance_sha=sha('research/batch48/provenance.json'),
    acceptance_checkpoint_sha=sha(p/'acceptance-checkpoint.json'),
    compiler='GCC15.2 CMake Release both;solution/simulator -O3 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic;CLI -O3 -DNDEBUG -std=c++17',
    baseline_scope='Actual R48 default archive54fc, distinct from historical measured991e. Candidate actual frozen Release25ac, distinct from functional O2 EXE17a3.',
    candidate_flags=acceptance['compile_flags'],
    scripts={str(path): sha(path) for path in map(Path, [
        'scripts/paired_benchmark_batch51.py', 'scripts/host_sampler_batch51.py',
        'scripts/compare_research.py', 'scripts/run_paired_batch51.py',
        'scripts/prepare_paired_plan_batch51.py'])},
    datasets={path: sha(path) for path in [
        'data/hard-corpus-resumed.json', 'data/projection-retention-heldout-batch45.json']},
    rounds=3,
    order='before/after,after/before,before/after per dataset;hard202 then heldout48',
    scope='All202 and all48, success and every failure retained;common success/failure/recovered costs separated;side median and median paired ratio distinguished',
    host_load=dict(
        measurement='Each complete CLI trial: host GetSystemTimes and GlobalMemoryStatusEx endpoints plus 0.25s samples;raw samples and integer deltas saved per trial',
        cpu='Host busy=(delta kernel+delta user-delta idle)/(delta kernel+delta user);includes benchmark and background;kernel includes idle',
        ram='Sampled available physical bytes with min/start/end;not process WS or simulated device capacity',
        api_failure='Preserve partial_or_unmeasured and API errors;no silent fabricated values',
        overhead='Same new monitoring harness both sides;no automatic rerun for incomplete observations',
        background='User apps untouched;unique project performance window does not imply an idle host'),
    default_unchanged_sha=sha('solution/solution.cpp'),
    default_exe_unchanged_sha=sha('build/aicore_bench.exe'),
    old_tex_unchanged_sha=sha('reports/project27-research.tex'),
    promotion='Forbidden before all actual trials and independent root cost review')
(p/'paired-plan.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
print('declaration only', sha(p/'paired-plan.json'), flush=True)
