"""Root-authorized environment-preflight revision; no algorithm changes."""
from pathlib import Path
import hashlib,json,shutil
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
old=Path('scripts/run_causal_reference_batch56.py');new=Path('scripts/run_causal_reference_revision1_batch56.py')
assert sha(old)=='9f302b3352161efb7878de53af7b13aca121cd3740af4b8c1e59b536c88fae04'
assert not new.exists()
text=old.read_text(encoding='utf-8');before='assert shutil.disk_usage(Path.cwd().anchor).free>=1<<30'
assert text.count(before)==1
new.write_text(text.replace(before,'assert shutil.disk_usage(Path.cwd().anchor).free>=1<<27',1),encoding='utf-8',newline='\n')
base=Path('research/batch56');outputs=[base/n for n in ('gold160.json','gold-driver-input.json','literal-charge-gold.json','fixture-qualifier-summary.json')]
assert not any(p.exists() for p in outputs) and not (base/'reference-execution-status.json').exists()
doc=dict(status='FRESH_PREFLIGHT_BEFORE_FIRST_ACTUAL_REFERENCE_CALL',F_free_bytes=shutil.disk_usage(Path.cwd().anchor).free,
         old_threshold_bytes=1<<30,new_small_reference_threshold_bytes=1<<27,
         reason='Root scope decision: original645138exit1 occurred before subprocess.run; generator_calls0. Environment preflight revision, not algorithm/gold repair or restarting an executed generator.',
         only_wrapper_semantic_change='1GiB to128MiB free-space threshold; all output-nonexistence/priorSHA/derived75-127 guards unchanged',
         generator_calls_so_far=0,outputs=[dict(path=str(p),exists=p.exists()) for p in outputs],
         files=[dict(path=str(p),sha256=sha(p)) for p in [old,new,Path(__file__),base/'reference-preflight-initial-failure.json',base/'reference-preflight-initial.stderr.txt',base/'source-before-gold-freeze.json',base/'fee-erratum-freeze-revision1.json',Path('scripts/make_causal_deferral_gold_batch56.py')]])
(base/'reference-preflight-revision1.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(new_wrapper_sha256=sha(new),fresh_snapshot_sha256=sha(base/'reference-preflight-revision1.json'),F_free_bytes=doc['F_free_bytes'])))
