"""Static file/SHA and handwritten-fee consistency only; no reference model."""
from pathlib import Path
import hashlib,json
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('research/batch56')
assert sha(p/'source-before-gold-freeze.json')=='3904f54639a8aa4d44102e5a681c40dff9d54559de641c371660913aa8dfd43e'
assert sha(p/'literal-hand-trace.json')=='a8b905dc4248bb1df438c2adcf0bb685b2296a300d8a2f228aa6e4190ef500ca'
assert sha(p/'solution.cpp')=='3a4f184de2759fdcd1cbfd899c5f8029e2f7f2691743ec214a895123db19c21a'
assert sha('scripts/make_causal_deferral_gold_batch56.py')=='495c6d82a877dd111163f2f636ffac657802e08879041791262d65669414f800'
trace=json.loads((p/'literal-hand-trace-revision1.json').read_text());total=0
for op,fee,cumulative in trace['operations']:
    total+=fee;assert total==cumulative,(op,total,cumulative)
assert len(trace['operations'])==64 and total==127
paths=[p/'literal-hand-trace-revision1.json',p/'topology-and-fee-erratum-revision1.md',p/'literal-hand-trace.json',
       p/'source-before-gold-freeze.json',p/'solution.cpp',p/'charged-work-implementation.json',
       Path('scripts/make_causal_deferral_gold_batch56.py'),Path(__file__),Path('solution/solution.cpp'),Path('reports/project27-research.tex')]
out=dict(status='STATIC_ERRATUM_ONLY_NO_REFERENCE_BATCH_COMPILER_SOLVER',initial_error_preserved=True,
         corrected_first_pair_fields=75,corrected_complete_scan=127,handwritten_rows=64,
         source_and_reference_generator_unchanged=True,topology='Original record-order FIFO in both Graph and context; no ID-heap in fee reference',
         files=[dict(path=f.as_posix(),sha256=sha(f),bytes=f.stat().st_size) for f in paths],
         default_unchanged=True,old_open_tex_unchanged=True,actual_candidate_executed=False,actual_reference_batch_executed=False,
         next='Root review before any independent reference generation or compile/solver.')
(p/'fee-erratum-freeze-revision1.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(rows=64,total=127,first_pair=75,freeze_sha256=sha(p/'fee-erratum-freeze-revision1.json'))))
