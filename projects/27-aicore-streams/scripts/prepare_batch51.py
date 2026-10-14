"""Dynamic cut gets <=2M within original shared16M; original seeds unchanged."""
from pathlib import Path
import hashlib
p=Path('research/batch51');p.mkdir(exist_ok=True)
oldfrag=Path('research/batch48/projection.cpp.inc').read_text(encoding='utf-8')
cut=Path('research/batch51/release-cut.cpp.inc').read_text(encoding='utf-8')
old='ShallowResult projection_memory_search(const HardwareInfo& h,const Graph& g,I work_limit=16000000)'
assert oldfrag.count(old)==1
wrapper='''
ShallowResult projection_memory_search(const HardwareInfo& h,const Graph& g,I work_limit=16000000) {
  auto cut=release_cut_order(h,g,std::min<I>(2000000,work_limit));
  if(cut.order.size()==static_cast<size_t>(g.n))return cut;
  auto original=projection_memory_search_r48(h,g,work_limit-cut.work);
  original.work+=cut.work;original.evaluations+=cut.evaluations;
  return original;
}
'''
newfrag=cut+'\n'+oldfrag.replace(old,old.replace('projection_memory_search(','projection_memory_search_r48('),1)+wrapper
(p/'projection.cpp.inc').write_text(newfrag,encoding='utf-8')
full=Path('research/batch48/solution.cpp').read_text(encoding='utf-8');assert full.count(oldfrag)==1
(p/'solution.cpp').write_text(full.replace(oldfrag,newfrag,1),encoding='utf-8')
for f in ('diagnostic.cpp','test_projection.cpp'):(p/f).write_bytes(Path('research/batch48',f).read_bytes())
print(hashlib.sha256((p/'solution.cpp').read_bytes()).hexdigest(),flush=True)
