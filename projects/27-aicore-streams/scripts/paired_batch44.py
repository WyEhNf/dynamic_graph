"""Predeclared R43/R44 same-Release full-corpus costs; no dropped failures."""
import hashlib,json,subprocess,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before='research/batch43/default-aicore_bench.exe';after='research/batch44/build/aicore_bench.exe';source='research/batch44/solution.cpp'
manifest=json.loads(Path('research/batch44/candidate-provenance.json').read_text());assert manifest['source_sha']==sha(source) and manifest['release_exe']==sha(after)
plan=dict(status='declared_before_execution',baseline_source=sha('research/batch43/solution.cpp'),candidate_source=sha(source),baseline_exe=sha(before),candidate_exe=sha(after),candidate_manifest_sha=sha('research/batch44/candidate-provenance.json'),compiler='GCC15.2 CMake Release -O3 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic both',datasets={p:sha(p) for p in ['data/hard-corpus-resumed.json','data/shallow-heldout-batch44.json']},rounds=3,order='before/after, after/before, before/after per dataset',scope='all202 and all72 incl all failures; common successes, common failures and recoveries separate; per-pair ratios and independent-side medians both; full CLI wall and working set; no36 repeat',window='Root-authorized after19 session45883 terminal, 18 and root static',source_unchanged_default=sha('solution/solution.cpp'))
Path('research/batch44/paired-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print('frozen paired-plan SHA',sha('research/batch44/paired-plan.json'),flush=True)
started=time.perf_counter()
for label,data in [('hard','data/hard-corpus-resumed.json'),('heldout','data/shallow-heldout-batch44.json')]:
    subprocess.run(['C:/Users/admin/miniconda3/python.exe','scripts/paired_benchmark.py','--baseline',before,'--current',after,'--current-source',source,'--suite',data,'--prefix',f'reports/paired-{label}-batch44','--repetitions','3','--allow-after-failures'],check=True)
assert sha(source)==plan['candidate_source'] and sha(before)==plan['baseline_exe'] and sha(after)==plan['candidate_exe']
print('R44 paired complete wall',time.perf_counter()-started,flush=True)
