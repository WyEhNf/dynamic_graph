"""Python bigint floor after full multiplication; exact frozen seed controls."""
import random
from pathlib import Path
M=(1<<63)-1;r=random.Random(2026101142);triples=[]
for a in [0,1,M,M-1,M//1024,6*10**18]:
 for b in [0,1,2,1024,2**31,1024*(2**31-1)]:
  for d in [1,2,3,M,M+1]:triples.append((a,b,d))
for _ in range(20000):triples.append((r.randrange(M+1),r.choice([1024,r.randrange(2**42)]),r.randrange(1,M+2)))
Path('data/priority-gold-batch42.txt').write_text('\n'.join(f'{a} {b} {d} {min(M,a*b//d)}' for a,b,d in triples),encoding='ascii')
print(len(triples),'exact bigint floor-mul-div controls')
