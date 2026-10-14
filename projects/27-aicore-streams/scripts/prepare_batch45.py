from pathlib import Path
import hashlib
p=Path('research/batch45');p.mkdir(exist_ok=True)
source=Path('research/batch44/solution.cpp').read_text(encoding='utf-8')
fragment=(p/'projection.cpp.inc').read_text(encoding='utf-8')
source=source.replace('std::vector<int> sink_projection_order(',fragment+'\nstd::vector<int> sink_projection_order(',1)
(p/'solution.cpp').write_text(source,encoding='utf-8')
diagnostic=Path('research/batch44/diagnostic.cpp').read_text(encoding='utf-8').replace('shallow_shape(g)','workspace_projection(g)').replace('shape.consumers.empty()','shape.targets.empty()').replace('shallow_profile(h,g,shape,shape.consumers)','projection_profile(h,g,shape,shape.targets)').replace('shallow_memory_search(h,g)','projection_memory_search(h,g)').replace('shape.producers.size()','0').replace('shape.consumers.size()','shape.targets.size()').replace('shape.tails.size()','0').replace('shallow,','workspace projections,')
(p/'diagnostic.cpp').write_text(diagnostic,encoding='utf-8')
print('candidate only',hashlib.sha256((p/'solution.cpp').read_bytes()).hexdigest())
