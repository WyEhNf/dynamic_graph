"""Static revision supplement materialization only; does not invoke resource API or children."""
from pathlib import Path
import hashlib,json
P=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
prior_path=P/'compiler-controls-plan-freeze.json'
assert sha(prior_path)=='433993db601ffdf6f8a30201904836e54a49ecdfbe3db21da573de45141eb3b1'
old=json.loads(prior_path.read_text())
for f in old['files']:assert sha(f['path'])==f['sha256'],f['path']
plan=json.loads((P/'compiler-resource-plan.json').read_text())
assert not Path(plan['owned_root']).exists()
plan.update(status='STATIC_REVISION1_RESOURCE_PREFLIGHT_SUPPLEMENT_NOT_EXECUTED',minimum_available_RAM_bytes=1<<30,minimum_F_free_small_state_bytes=1<<26,RAM_source='Actual GlobalMemoryStatusEx.ullAvailPhys fresh before every child; API failure blocks execution',initial_preflight_failure='Save actualstatus/raw and exit before creating G workspace/child; no restart',prior_plan_sha256=sha(P/'compiler-resource-plan.json'),prior_runner_sha256=sha('scripts/run_causal_controls_batch56.py'),prior_freeze_sha256=sha(prior_path))
target=P/'compiler-resource-plan-revision1.json';assert not target.exists();target.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
paths=[str(target),str(prior_path),str(P/'compiler-resource-plan.json'),'scripts/run_causal_controls_batch56.py','scripts/run_causal_controls_revision1_batch56.py','scripts/prepare_causal_preflight_revision1_batch56.py',str(P/'compiler-preflight-supplement-revision1.md')]
doc=dict(status='SOURCE_ONLY_REVISION1_FROZEN_NOT_EXECUTED',prior_freeze_sha256=sha(prior_path),prior_frozen_files_count=len(old['files']),candidate_source_sha256=sha(P/'solution.cpp'),candidate_executed=False,compiled=False,no_live_handles=[],default_changed=False,old_open_tex_changed=False,files=[dict(path=f,sha256=sha(f),bytes=Path(f).stat().st_size) for f in paths])
target=P/'compiler-controls-plan-freeze-revision1.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(path=str(target),sha256=sha(target),runner_revision1_sha256=sha('scripts/run_causal_controls_revision1_batch56.py'),plan_revision1_sha256=sha(P/'compiler-resource-plan-revision1.json'),files=len(paths),prior_freeze_sha256=sha(prior_path),executed=False),indent=2))
