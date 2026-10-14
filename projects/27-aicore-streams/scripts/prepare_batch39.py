"""Move a cheap structural recognizer ahead of failed general frontier search."""
from pathlib import Path
base=Path('research/batch39');base.mkdir(parents=True,exist_ok=True)
s=Path('research/batch38/solution.cpp').read_text(encoding='utf-8')
begin=s.rindex('  if(!found && graph.n<=4096) {\n    auto order=strict_fork_join_order(graph);')
end=s.index('  metrics.micros=',begin)
block=s[begin:end];s=s[:begin]+s[end:]
at=s.rindex('  if(!found && graph.n<=768) {')
s=s[:at]+block+s[at:]
(base/'solution.cpp').write_text(s,encoding='utf-8')
print('Created batch39: same structural candidate before costly frontier failures')
