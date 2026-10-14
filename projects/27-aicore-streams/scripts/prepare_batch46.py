"""Only interface recognition changes; fixed R45 search budget and moves."""
from pathlib import Path
import hashlib
p=Path('research/batch46');p.mkdir(exist_ok=True)
old='I threshold=priority_mul_div(positive[(positive.size()-1)/2],4,1);'
new='''// A gap is an input feature, never a dependency/memory transformation.
  // Positive integer division avoids multiplication overflow at full int64.
  // If no >=4 ratio separates workspace populations, keep all local maxima
  // eligible rather than rejecting every one because the median is high.
  I threshold=positive.front(),best_ratio=3;
  for(size_t q=1;q<positive.size();++q) {
    I ratio=positive[q]/positive[q-1];
    if(ratio>best_ratio){best_ratio=ratio;threshold=positive[q];}
  }'''
for file in ['solution.cpp','projection.cpp.inc']:
    s=Path('research/batch45',file).read_text(encoding='utf-8');assert old in s
    (p/file).write_text(s.replace(old,new,1),encoding='utf-8')
for file in ['diagnostic.cpp','test_projection.cpp']:(p/file).write_bytes(Path('research/batch45',file).read_bytes())
script=Path('scripts/make_projection_gold_batch45.py').read_text(encoding='utf-8')
script=script.replace('threshold=min(MAX,4*positive[(len(positive)-1)//2])','threshold=positive[0]; best_ratio=3\n    for previous,next_work in zip(positive,positive[1:]):\n        ratio=next_work//previous\n        if ratio>best_ratio:best_ratio=ratio;threshold=next_work')
script=script.replace('batch45','batch46')
Path('scripts/make_projection_gold_batch46.py').write_text(script,encoding='utf-8')
print('isolated gap candidate',hashlib.sha256((p/'solution.cpp').read_bytes()).hexdigest())
