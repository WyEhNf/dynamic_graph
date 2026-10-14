"""Preserve first readonly report; restrict diagnostic target bound to future J only."""
from pathlib import Path
import hashlib,json
P=Path('research/batch56');old=Path('scripts/analyze_causal_guard_prefix_batch56.py');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'actual-guard-prefix-attribution.json')=='98c1dbb84461a1c53c831755840006e0e8714657e3e25337b55b64106cc498f5'
s=old.read_text();s=s.replace("if first is None and before<=f['hardware']['memory_limit']<forced:","if j not in prefix[:k] and first is None and before<=f['hardware']['memory_limit']<forced:")
s=s.replace("target_final_bound=forced,first_new_guard_bound_crossing=first", "target_final_bound=forced if j not in D else None,target_completed_scope='Bound applies only before selected J Compute; selected J already completed so no final bound claim' if j in D else 'Selected J remains unfinished; final bound is a necessary future Compute bound',first_new_guard_bound_crossing=first")
s=s.replace("status='READONLY_ACTUAL_GUARD_PREFIX_BIGINT_ATTRIBUTION'", "status='READONLY_ACTUAL_GUARD_PREFIX_BIGINT_ATTRIBUTION_REVISION1_FUTURE_TARGET_SCOPE',prior_report_sha256=sha(P/'actual-guard-prefix-attribution.json'),erratum='Initial fixed-J arithmetic after J completed is not a necessary future bound; all-unfinished-target checks were correct and stay unchanged.'")
s=s.replace("target=P/'actual-guard-prefix-attribution.json'", "target=P/'actual-guard-prefix-attribution-revision1.json'")
target=Path('scripts/analyze_causal_guard_prefix_revision1_batch56.py');assert not target.exists();target.write_text(s,encoding='utf-8')
doc=dict(status='STATIC_READONLY_DIAGNOSTIC_SCOPE_REVISION_ONLY',prior_script_sha256=sha(old),prior_report_sha256=sha(P/'actual-guard-prefix-attribution.json'),revision_script_sha256=sha(target),reason='Selected J in018 has completed; do not label later fixed-target pin sum as necessary obstruction. 023 J remains unfinished and valid2475 witness unchanged.',solver_executed=False,default_changed=False)
target=P/'guard-attribution-erratum-revision1.json';assert not target.exists();target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps(doc,indent=2))
