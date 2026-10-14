"""Freeze static source/fee/generator BEFORE calculating gold or compiling."""
from pathlib import Path
import hashlib,json
P=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
paths=['research/batch56/solution.cpp','research/batch56/causal-detector.cpp.inc','research/batch56/causal.cpp.inc',
       'research/batch56/release-cut.cpp.inc','research/batch56/source-provenance.json','research/batch56/charged-work-implementation.json',
       'research/batch56/literal-hand-trace.json','research/batch56/gold-driver.cpp','research/batch56/static-design.md',
       'research/batch56/gold-declaration.json','research/batch56/static-plan-freeze.json',
       'scripts/prepare_causal_deferral_source_batch56.py','scripts/make_causal_deferral_gold_batch56.py',__file__,
       'research/batch51/solution.cpp','research/batch51/release-cut.cpp.inc','solution/solution.cpp',
       'build/aicore_bench.exe','reports/project27-research.tex','research/batch55/negative-checkpoint.json']
assert sha('solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
doc=dict(status='SOURCE_ONLY_BEFORE_REFERENCE_GOLD_COMPILE_OR_SOLVER',source_sha256=sha('research/batch56/solution.cpp'),
         files=[dict(path=f,sha256=sha(f),bytes=Path(f).stat().st_size) for f in paths],
         predeclared_fixture_count=160,actual_generated160=False,actual_candidate_executed=False,
         compiler_executed=False,normal_default_unchanged=True,old_open_tex_unchanged=True,
         window='Static writes only while parent19 resourcewindow preparation; no calculation tests.',
         next='One source-only independent Python gold materialization when root permits; freeze gold before requesting GCC/UBSan execution.')
(P/'source-before-gold-freeze.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(paths),source_sha256=doc['source_sha256'],freeze_sha256=sha(P/'source-before-gold-freeze.json'))))
