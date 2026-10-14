"""Read-only hash/evidence freeze; run outside another project's CPU window."""
import hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
core=Path('research/batch44/solution.cpp');fragment=Path('research/batch44/shallow.cpp.inc')
assert fragment.read_text(encoding='utf-8') in core.read_text(encoding='utf-8')
assert '#include "shallow.cpp.inc"' not in core.read_text(encoding='utf-8')
functional=json.loads(Path('reports/functional-summary-batch44.json').read_text());assert functional['source_sha']==sha(core)
profiles=Path('reports/shallow-profile-ubsan-batch44.txt').read_text(encoding='utf-8');assert '2590 independent' in profiles and '160 bounded search' in profiles
numeric={}
for label in ['numeric-controls','numeric-parallel','numeric-parallel-valid','scaled-serial']:
    p=Path(f'reports/{label}-ubsan-batch44.json');r=json.loads(p.read_text());assert r['passed']==r['total'];numeric[label]=dict(total=r['total'],passed=r['passed'],report_sha=sha(p))
inputs=['research/batch44/solution.cpp','include/problem.h','src/benchmark.cpp','src/simulator.cpp','include/simulator.h','include/local_json.h','include/solver_metrics.h','CMakeLists.txt']
generation=['research/batch43/solution.cpp','research/batch44/shallow.cpp.inc','scripts/prepare_batch44.py','scripts/make_shallow_gold_batch44.py','scripts/make_shallow_holdout_batch44.py']
tests=['research/batch44/test_shallow.cpp','research/batch44/numeric_checks.cpp','research/batch44/build-numeric-ubsan.cmd','research/batch44/build-shallow-ubsan.cmd']
data=['data/hard-corpus-resumed.json','data/nested-forkjoin-new-batch38.json','data/shallow-profile-gold-batch44.json','data/shallow-heldout-batch44.json']
flags=['research/batch44/build/CMakeFiles/solution.dir/flags.make','research/batch44/build/CMakeFiles/aicore_bench.dir/flags.make','research/batch44/build/CMakeFiles/simulator.dir/flags.make']
manifest=dict(status='validated_candidate_not_default',source_sha=sha(core),single_file='fragment expanded inside source; problem.h plus standard library only',functional_source_exe=sha('research/batch44/aicore_bench.exe'),release_exe=sha('research/batch44/build/aicore_bench.exe'),default_source_unchanged=sha('solution/solution.cpp'),compile_inputs={p:sha(p) for p in inputs},generation_inputs={p:sha(p) for p in generation},test_inputs={p:sha(p) for p in tests},data_inputs={p:sha(p) for p in data},release_flags={p:Path(p).read_text() for p in flags},profile_gold=2590,bounded_search_validity=160,adjacent_exchange=756,numeric_fixed_plan=numeric,functional_report_sha=sha('reports/functional-summary-batch44.json'),functional=functional['comparisons'],regression=json.loads(Path('reports/regression-batch44.json').read_text()),timing_caveat='Functional O2/new vs O3/old shared CPU is not a performance ratio; coordinated same-Release pairs pending',LF_console_hash_error='Old prepare printed normalized text hash; fixed to actual file bytes. Functional artifacts always had read_bytes SHA.')
Path('research/batch44/candidate-provenance.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8');print(manifest['source_sha'],manifest['release_exe'])
