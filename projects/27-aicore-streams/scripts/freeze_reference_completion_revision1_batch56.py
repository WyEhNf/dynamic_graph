"""Append final provenance, preserving original failed preflight and gold freeze."""
from pathlib import Path
import hashlib,json
P=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
s=json.loads((P/'reference-execution-status.json').read_text());assert s['actual_exit_code']==0
paths=[P/'pre-compile-gold-freeze.json',P/'reference-preflight-revision1.json',P/'reference-preflight-initial-failure.json',
       P/'reference-preflight-initial.stderr.txt',P/'reference-execution-status.json',P/'reference.stdout.txt',P/'reference.stderr.txt',
       P/'gold160.json',P/'gold-driver-input.json',P/'literal-charge-gold.json',P/'fixture-qualifier-summary.json',
       P/'source-before-gold-freeze.json',P/'fee-erratum-freeze-revision1.json',P/'literal-hand-trace.json',P/'literal-hand-trace-revision1.json',
       P/'solution.cpp',Path('scripts/run_causal_reference_batch56.py'),Path('scripts/run_causal_reference_revision1_batch56.py'),
       Path('scripts/prepare_reference_wrapper_revision1_batch56.py'),Path(__file__),Path('scripts/make_causal_deferral_gold_batch56.py'),
       Path('solution/solution.cpp'),Path('reports/project27-research.tex')]
out=dict(status='ACTUAL_ONCE_REFERENCE_TERMINAL_EXIT0_NO_CANDIDATE',actual_exit_code=0,actual_owner_pid=s['owner_pid'],
         live_handles=[],actual_generator_calls=1,prior_environment_preflight_exit=1,prior_generator_calls=0,
         scope_decision='Root authorized changing only pure-reference free-space gate1GiB to128MiB; not algorithm/gold repair or restart of executed generator.',
         reference_count=160,qualified_pairs=96,exhausted=12,whole_fixed_physical_legal=144,whole_fixed_physical_expected_invalid=16,
         basic_literal_first_pair=75,basic_literal_complete_scan=127,not_ready_first_pair=143,not_ready_complete_scan=205,
         old_hand_error_preserved=True,hand_correction_before_reference=True,
         candidate_executed=False,compiler_executed=False,solver_executed=False,default_unchanged=True,old_open_tex_unchanged=True,
         files=[dict(path=f.as_posix(),sha256=sha(f),bytes=f.stat().st_size) for f in paths],
         next='Root independent code/gold review; no candidate compile or original12/63 solver authorized yet.')
(P/'reference-completion-freeze-revision1.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(paths),freeze_sha256=sha(P/'reference-completion-freeze-revision1.json'))))
