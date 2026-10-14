"""Only add first-member pivot to frozen R48; do not inherit R49 size16."""
from pathlib import Path
import hashlib
p=Path('research/batch50');p.mkdir(exist_ok=True)
old='for(int pivot:{critical,critical+1})';new='for(int pivot:{critical,critical+1,first})'
for file in ('solution.cpp','projection.cpp.inc'):
    s=Path('research/batch48',file).read_text(encoding='utf-8');assert s.count(old)==1
    (p/file).write_text(s.replace(old,new,1),encoding='utf-8')
for file in ('diagnostic.cpp','test_projection.cpp','test_group_template.cpp'):(p/file).write_bytes(Path('research/batch48',file).read_bytes())
print(hashlib.sha256((p/'solution.cpp').read_bytes()).hexdigest(),flush=True)
