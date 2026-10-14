"""New structural Python tasks, fixed before their first model evaluation.

This is a small self-created holdout, not a real-repository benchmark. Tests
and reference implementations are outside model snapshots. Once used to
tune a policy its status must change to development data.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

from .bundles import digest_tree
from .engineering_suite import COMPAT, COMMON_TEST, PRESERVE
from .selftest_suite import build_suite


VALIDATORS = '''from config import MAX_SIZE
def checked_size(n):
    if not isinstance(n,int) or n<0 or n>MAX_SIZE:
        raise ValueError("size")
    return n
def checked_vertex(v,n):
    if not isinstance(v,int) or not 0<=v<n:
        raise ValueError("vertex")
    return v
'''

# name, public specification, reference code, trusted tests, dependencies,
# existing imports and target function declaration.
TASKS = [
('stable_topology',
 'Implement stable_topology(n, edges) for a directed graph with integer vertices 0 through n-1. Call checked_size from helpers.py for n and checked_vertex from helpers.py for every endpoint. Repeated edges count only once. Repeatedly choose the smallest currently zero-indegree vertex; return the resulting new list. Cycles and invalid vertices raise ValueError. The empty graph returns []. Never modify edges.',
 '''from helpers import checked_size,checked_vertex
def stable_topology(n,edges):
    checked_size(n)
    links=set()
    for u,v in edges:
        checked_vertex(u,n); checked_vertex(v,n); links.add((u,v))
    remaining=set(range(n)); result=[]
    while remaining:
        ready=[v for v in remaining if not any(b==v and a in remaining for a,b in links)]
        if not ready: raise ValueError("cycle")
        v=min(ready); remaining.remove(v); result.append(v)
    return result
''',
 '''from solution import stable_topology
class Check(unittest.TestCase):
    def test_random_dags(self):
        import random
        rng=random.Random(110801)
        for n in range(9):
            for _ in range(20):
                order=list(range(n)); rng.shuffle(order)
                edges=[(order[i],order[j]) for i in range(n) for j in range(i+1,n) if rng.random()<.35]
                if edges: edges+=edges[:2]
                rng.shuffle(edges); before=edges[:]
                adj=[set() for _ in range(n)]; indeg=[0]*n
                for u,v in set(edges): adj[u].add(v); indeg[v]+=1
                expected=[]; ready=[i for i in range(n) if not indeg[i]]
                while ready:
                    ready.sort(); u=ready.pop(0); expected.append(u)
                    for v in adj[u]:
                        indeg[v]-=1
                        if not indeg[v]: ready.append(v)
                self.assertEqual(stable_topology(n,edges),expected); self.assertEqual(edges,before)
    def test_invalid(self):
        for n,edges in [(2,[(0,1),(1,0)]),(1,[(0,0)]),(2,[(0,2)]),(-1,[]),(65,[])]:
            with self.assertRaises(ValueError): stable_topology(n,edges)
''', {'helpers.py':VALIDATORS,'config.py':'MAX_SIZE=64\n'},
 'from helpers import checked_size,checked_vertex\ndef stable_topology(n,edges):\n'),
('shortest_layers',
 'Implement shortest_layers(n, edges, start). Call checked_size and checked_vertex from helpers.py to validate n, start and all directed edge endpoints, including unreachable edges. Return a new list of lists grouping reachable vertices by shortest edge distance from start, with each group numerically sorted. Duplicate edges and cycles are allowed. The first group is [start]. Invalid inputs raise ValueError. Do not modify edges.',
 '''from helpers import checked_size,checked_vertex
def shortest_layers(n,edges,start):
    checked_size(n); checked_vertex(start,n)
    adj=[set() for _ in range(n)]
    for u,v in edges:
        checked_vertex(u,n); checked_vertex(v,n); adj[u].add(v)
    seen={start}; frontier=[start]; result=[]
    while frontier:
        result.append(sorted(frontier))
        following=set()
        for u in frontier: following.update(adj[u])
        following-=seen; seen.update(following); frontier=list(following)
    return result
''',
 '''from solution import shortest_layers
class Check(unittest.TestCase):
    def test_distances(self):
        import random
        rng=random.Random(110802)
        for n in range(1,10):
            for _ in range(15):
                edges=[(u,v) for u in range(n) for v in range(n) if rng.random()<.2]; start=rng.randrange(n); before=edges[:]
                distance=[n+1]*n; distance[start]=0
                for _ in range(n):
                    for u,v in edges: distance[v]=min(distance[v],distance[u]+1)
                expected=[[v for v in range(n) if distance[v]==d] for d in range(n)]
                expected=[layer for layer in expected if layer]
                self.assertEqual(shortest_layers(n,edges,start),expected); self.assertEqual(edges,before)
    def test_validate_unreachable(self):
        for n,edges,start in [(3,[(2,3)],0),(0,[],0),(3,[],-1),(65,[],0)]:
            with self.assertRaises(ValueError): shortest_layers(n,edges,start)
''', {'helpers.py':VALIDATORS,'config.py':'MAX_SIZE=64\n'},
 'from helpers import checked_size,checked_vertex\ndef shortest_layers(n,edges,start):\n'),
('interval_gaps',
 'Implement interval_gaps(intervals, lower, upper). Endpoints are integers representing half-open intervals. If lower is greater than upper, or any interval start is greater than its end, raise ValueError even for an interval outside the bounds. Clip intervals to [lower, upper), merge overlap and touching coverage, and return sorted maximal uncovered half-open intervals as a new list of tuples. Zero-length intervals cover nothing. Equal bounds return [] after validating intervals. Do not modify intervals.',
 '''def interval_gaps(intervals,lower,upper):
    if lower>upper: raise ValueError("bounds")
    clipped=[]
    for a,b in intervals:
        if a>b: raise ValueError("interval")
        a=max(a,lower); b=min(b,upper)
        if a<b: clipped.append((a,b))
    result=[]; cursor=lower
    for a,b in sorted(clipped):
        if a>cursor: result.append((cursor,a))
        cursor=max(cursor,b)
    if cursor<upper: result.append((cursor,upper))
    return result
''',
 '''from solution import interval_gaps
class Check(unittest.TestCase):
    def test_integer_coverage(self):
        import random
        rng=random.Random(110803)
        for _ in range(160):
            lo=rng.randrange(-10,5); hi=lo+rng.randrange(16)
            intervals=[tuple(sorted((rng.randrange(-15,20),rng.randrange(-15,20)))) for _ in range(rng.randrange(12))]
            before=intervals[:]; cells=[x for x in range(lo,hi) if not any(a<=x<b for a,b in intervals)]
            expected=[]
            for x in cells:
                if expected and expected[-1][1]==x: expected[-1]=(expected[-1][0],x+1)
                else: expected.append((x,x+1))
            self.assertEqual(interval_gaps(intervals,lo,hi),expected); self.assertEqual(intervals,before)
    def test_invalid_outside(self):
        for intervals,lo,hi in [([(100,99)],0,1),([(2,1)],0,0),([],3,2)]:
            with self.assertRaises(ValueError): interval_gaps(intervals,lo,hi)
''', {},'def interval_gaps(intervals,lower,upper):\n'),
('sparse_product',
 'Implement sparse_product(left, right, rows, inner, cols). Inputs are dictionaries mapping (row, column) pairs to integer values. Call checked_size from helpers.py for all three dimensions, and checked_vertex for both coordinates of every entry, including explicit zero entries. Return a new coordinate dictionary for the matrix product, omitting zero results. Invalid dimensions or coordinates raise ValueError. Empty dimensions are allowed when the entry dictionaries are empty. Never modify inputs.',
 '''from helpers import checked_size,checked_vertex
def sparse_product(left,right,rows,inner,cols):
    for n in (rows,inner,cols): checked_size(n)
    for i,k in left:
        checked_vertex(i,rows); checked_vertex(k,inner)
    for k,j in right:
        checked_vertex(k,inner); checked_vertex(j,cols)
    result={}
    for (i,k),a in left.items():
        for (q,j),b in right.items():
            if q==k: result[i,j]=result.get((i,j),0)+a*b
    return {key:value for key,value in result.items() if value!=0}
''',
 '''from solution import sparse_product
class Check(unittest.TestCase):
    def test_dense_oracle(self):
        import random
        rng=random.Random(110804)
        for _ in range(100):
            rows,inner,cols=[rng.randrange(5) for _ in range(3)]
            left={(i,k):rng.randrange(-3,4) for i in range(rows) for k in range(inner) if rng.random()<.5}
            right={(k,j):rng.randrange(-3,4) for k in range(inner) for j in range(cols) if rng.random()<.5}
            oldl=left.copy(); oldr=right.copy(); expected={}
            for i in range(rows):
                for j in range(cols):
                    value=sum(left.get((i,k),0)*right.get((k,j),0) for k in range(inner))
                    if value: expected[i,j]=value
            self.assertEqual(sparse_product(left,right,rows,inner,cols),expected)
            self.assertEqual(left,oldl); self.assertEqual(right,oldr)
    def test_zero_entry_validation(self):
        for left,right,shape in [({(0,2):0},{},(1,2,1)),({},{(-1,0):0},(1,2,1)),({},{},(-1,0,0)),({},{},(65,0,0))]:
            with self.assertRaises(ValueError): sparse_product(left,right,*shape)
''', {'helpers.py':VALIDATORS,'config.py':'MAX_SIZE=64\n'},
 'from helpers import checked_size,checked_vertex\ndef sparse_product(left,right,rows,inner,cols):\n'),
('allocate_round_robin',
 'Implement allocate_round_robin(demands, total). All demands and total are nonnegative integers; invalid values raise ValueError. Start a new allocation list of zeros and distribute one unit at a time to each not-yet-satisfied demand in original index order, repeating rounds. Stop when total is exhausted or every demand is satisfied. Surplus total is unused. Empty demands return [] after validating total. Do not modify demands or return its original list.',
 '''def allocate_round_robin(demands,total):
    if not isinstance(total,int) or total<0: raise ValueError("total")
    if any(not isinstance(d,int) or d<0 for d in demands): raise ValueError("demand")
    result=[0]*len(demands)
    while total:
        changed=False
        for i,d in enumerate(demands):
            if result[i]<d and total:
                result[i]+=1; total-=1; changed=True
        if not changed: break
    return result
''',
 '''from solution import allocate_round_robin
class Check(unittest.TestCase):
    def test_rounds(self):
        import random
        rng=random.Random(110805)
        for _ in range(160):
            demands=[rng.randrange(8) for _ in range(rng.randrange(9))]; total=rng.randrange(65); before=demands[:]
            recipients=[i for level in range(max(demands,default=0)) for i,d in enumerate(demands) if d>level]
            expected=[0]*len(demands)
            for i in recipients[:total]: expected[i]+=1
            result=allocate_round_robin(demands,total)
            self.assertEqual(result,expected); self.assertEqual(demands,before); self.assertIsNot(result,demands)
    def test_invalid(self):
        for demands,total in [([], -1),([-1],0),([1.5],2),([],1.5)]:
            with self.assertRaises(ValueError): allocate_round_robin(demands,total)
''', {},'def allocate_round_robin(demands,total):\n'),
('outer_join',
 'Implement outer_join(left, right), where each input is a list of (string key, value) pairs. Return a new list of (key, left_value, right_value) tuples. Visit left pairs in input order; for each, emit every matching right pair in right input order, preserving duplicates. If none matches, emit (key, left_value, None). After all left pairs, append right pairs whose key never occurs in left as (key, None, right_value), in right input order. Do not modify either input. Empty inputs follow the same rules.',
 '''def outer_join(left,right):
    result=[]; left_keys={key for key,value in left}
    for key,value in left:
        matches=[other for rkey,other in right if rkey==key]
        if matches: result.extend((key,value,other) for other in matches)
        else: result.append((key,value,None))
    result.extend((key,None,value) for key,value in right if key not in left_keys)
    return result
''',
 '''from solution import outer_join
class Check(unittest.TestCase):
    def test_duplicate_order(self):
        self.assertEqual(outer_join([("b",1),("a",2),("b",3)],[("b",4),("c",5),("b",6)]),[("b",1,4),("b",1,6),("a",2,None),("b",3,4),("b",3,6),("c",None,5)])
    def test_random(self):
        import random
        rng=random.Random(110806)
        for _ in range(160):
            left=[(rng.choice("abc"),rng.randrange(7)) for _ in range(rng.randrange(8))]
            right=[(rng.choice("abcd"),rng.randrange(7)) for _ in range(rng.randrange(8))]
            oldl=left[:]; oldr=right[:]; bykey={}
            for key,value in right: bykey.setdefault(key,[]).append(value)
            expected=[]
            for key,value in left:
                for other in bykey.get(key,[None]): expected.append((key,value,other))
            for key,value in right:
                if all(key!=k for k,v in left): expected.append((key,None,value))
            result=outer_join(left,right)
            self.assertEqual(result,expected); self.assertEqual(left,oldl); self.assertEqual(right,oldr)
''', {},'def outer_join(left,right):\n'),
]


def build_holdout(destination):
    if (destination/'manifest.json').exists():
        raise ValueError('holdout already exists; choose a fresh destination rather than overwrite evidence')
    cases=[(name,spec+PRESERVE,COMPAT+oracle,tests+COMMON_TEST,files)
           for name,spec,oracle,tests,files,declaration in TASKS]
    ids=build_suite(destination,cases,version=8)
    for name,spec,oracle,tests,files,declaration in TASKS:
        root=destination/'repo_bundles'/name
        (root/'solution.py').write_text(COMPAT+declaration+'    raise NotImplementedError("repair this function")\n',encoding='utf8')
        path=destination/'metadata'/f'{name}.json'
        meta=json.loads(path.read_text(encoding='utf8'))
        meta['pinned_files']=['solution.py']; meta['snapshot_sha256']=digest_tree(root)
        meta['split']='new structural holdout, not used for policy tuning before first evaluation'
        path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    manifest_path=destination/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    manifest['constructed_unix']=time.time()
    manifest['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest['limitations']='Six synthetic pure-function tasks; not independent real-repository coverage.'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return ids


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--destination',default='fixtures/structural-holdout-v8')
    args=parser.parse_args(); print(build_holdout(Path(args.destination)))


if __name__=='__main__': main()
