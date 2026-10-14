"""Fixed, synthetic workflow holdout; trusted tests never enter snapshots.

These dictionary/string workflows remain inside the pure-function evaluator.
They are not a substitute for executing arbitrary real-repository patches.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

from .bundles import digest_tree
from .engineering_suite import COMPAT, COMMON_TEST, PRESERVE
from .selftest_suite import build_suite


TASKS = [
    ("transactional_edits",
     "Implement transactional_edits(original, operations). original is a dictionary mapping string keys to integer values. Each operation is a tuple (action, key, value). Apply operations in order to a new dictionary. 'set' requires an integer value and sets or replaces key; 'add' requires an integer value and an existing key, then adds it; 'delete' requires value is None and an existing key, then removes it. Unknown actions, non-string keys, wrong values, or missing keys raise ValueError. Validate all original entries, even if operations later remove them. Call checked_integer from helpers.py for every original value and every set/add value. Never modify original or operations, even when a later operation fails. Return the new dictionary, including when operations is empty.",
     '''from helpers import checked_integer
def transactional_edits(original,operations):
    result={}
    for key,value in original.items():
        if not isinstance(key,str): raise ValueError("key")
        checked_integer(value); result[key]=value
    for action,key,value in operations:
        if not isinstance(key,str): raise ValueError("key")
        if action in ("set","add"):
            checked_integer(value)
            if action=="set": result[key]=value
            elif key in result: result[key]+=value
            else: raise ValueError("missing")
        elif action=="delete" and value is None and key in result:
            del result[key]
        else: raise ValueError("operation")
    return result
''',
     '''from solution import transactional_edits
class Check(unittest.TestCase):
    def test_sequences(self):
        import random
        rng=random.Random(111301)
        for _ in range(180):
            original={key:rng.randrange(-5,6) for key in "abc"}; expected=dict(original); operations=[]
            for j in range(15):
                key=rng.choice("abcd"); action=rng.choice(["set","add","delete"])
                if action!="set" and key not in expected: action="set"
                value=None if action=="delete" else rng.randrange(-4,5)
                operations.append((action,key,value))
                if action=="delete": del expected[key]
                elif action=="set": expected[key]=value
                else: expected[key]=expected[key]+value
            before=dict(original); oldops=operations[:]
            answer=transactional_edits(original,operations)
            self.assertEqual(answer,expected); self.assertIsNot(answer,original)
            self.assertEqual(original,before); self.assertEqual(operations,oldops)
    def test_failure_atomicity(self):
        for operations in [[("set","a",8),("add","missing",2)],[("delete","a",None),("x","b",1)],[("set","x",1.2)],[("delete","a",0)],[("set",2,3)]]:
            original={"a":3}; before=dict(original)
            with self.assertRaises(ValueError): transactional_edits(original,operations)
            self.assertEqual(original,before)
        with self.assertRaises(ValueError): transactional_edits({"bad":"3"},[("delete","bad",None)])
    def test_helper_boundary(self):
        import helpers
        old=helpers.checked_integer; seen=[]
        def track(value): seen.append(value); return old(value)
        helpers.checked_integer=track
        try:
            import importlib,solution
            importlib.reload(solution)
            self.assertEqual(solution.transactional_edits({"a":7},[("set","b",4),("add","a",2)]),{"a":9,"b":4})
            self.assertEqual(seen,[7,4,2])
        finally:
            helpers.checked_integer=old
            importlib.reload(solution)
''',
     {"config.py": 'VALUE_KINDS=[]\nfor kind in (int,):\n    VALUE_KINDS.append(kind)\nINTEGER_KIND=VALUE_KINDS[0]\n',
      "helpers.py": 'from config import INTEGER_KIND\ndef checked_integer(value):\n    if not isinstance(value,INTEGER_KIND): raise ValueError("integer")\n    return value\n'},
     'from helpers import checked_integer\ndef transactional_edits(original,operations):\n'),
    ("merge_config",
     "Implement merge_config(base, override). Each input is a nested dictionary with string keys; leaf values are integers, strings, or None. Recursively merge a pair of dictionary values. Every other override value replaces the base value. An override value of None deletes that key if present; None in base is an ordinary value. Missing deletes are harmless. Validate every key and leaf in both complete inputs before merging, including overwritten and deleted branches; invalid types raise ValueError. Return independent dictionaries at every level, including unchanged or newly inserted subtrees. Do not mutate either input. Dictionary insertion order is not part of the contract.",
     '''def merge_config(base,override):
    def validate(node):
        if not isinstance(node,dict): raise ValueError("mapping")
        for key,value in node.items():
            if not isinstance(key,str): raise ValueError("key")
            if isinstance(value,dict): validate(value)
            elif value is not None and not isinstance(value,(int,str)): raise ValueError("leaf")
    def copy_value(value):
        return {k:copy_value(v) for k,v in value.items()} if isinstance(value,dict) else value
    def combine(left,right):
        result=copy_value(left)
        for key,value in right.items():
            if value is None: result.pop(key,None)
            elif isinstance(value,dict) and isinstance(result.get(key),dict): result[key]=combine(result[key],value)
            else: result[key]=copy_value(value)
        return result
    validate(base); validate(override)
    return combine(base,override)
''',
     '''from solution import merge_config
class Check(unittest.TestCase):
    def test_recursive(self):
        import copy,random
        rng=random.Random(111302)
        def tree(depth):
            out={}
            for key in "abcd":
                if rng.random()<.6: out[key]=tree(depth-1) if depth and rng.random()<.45 else rng.choice([None,-2,4,"x"])
            return out
        def expected(left,right):
            result=copy.deepcopy(left)
            for k,v in right.items():
                if v is None: result.pop(k,None)
                elif isinstance(v,dict) and isinstance(left.get(k),dict): result[k]=expected(left[k],v)
                else: result[k]=copy.deepcopy(v)
            return result
        for _ in range(160):
            base=tree(3); override=tree(3); oldb=copy.deepcopy(base); oldo=copy.deepcopy(override)
            self.assertEqual(merge_config(base,override),expected(base,override))
            self.assertEqual(base,oldb); self.assertEqual(override,oldo)
    def test_no_nested_alias(self):
        base={"stay":{"x":1},"merge":{"a":2},"none":None}; override={"new":{"y":3},"merge":{"b":4}}
        out=merge_config(base,override); out["stay"]["x"]=8; out["new"]["y"]=9; out["merge"]["a"]=0
        self.assertEqual(base,{"stay":{"x":1},"merge":{"a":2},"none":None})
        self.assertEqual(override,{"new":{"y":3},"merge":{"b":4}})
        self.assertEqual(merge_config({"a":None},{"z":None}),{"a":None})
    def test_full_validation(self):
        for base,override in [({"x":{"bad":[]}}, {"x":None}),({"x":1},{"x":2.4}),({1:3},{1:None}),({"x":1},{"x":{2:3}}),([],{}),({},None)]:
            with self.assertRaises(ValueError): merge_config(base,override)
''', {}, 'def merge_config(base,override):\n'),
    ("patch_text",
     "Implement patch_text(text, edits). text is a string. Each edit is (start, end, replacement), where start/end are integer offsets into the ORIGINAL string, 0<=start<=end<=len(text), and replacement is a string. Reject invalid offsets or replacement types with ValueError. Nonempty deleted intervals must not overlap. Zero-length insertions may lie at deletion endpoints, but strictly inside a deletion is invalid. Apply using original coordinates: visit positions in increasing order; at a position emit all zero-length insertions in their input order, then any nonempty edit starting there; an insertion at a deletion end is therefore emitted at the next visited position. Unedited characters remain unchanged. Do not modify edits. Return the resulting string. Validate every edit before constructing the answer.",
     '''def patch_text(text,edits):
    normalized=[]
    for index,(start,end,replacement) in enumerate(edits):
        if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<=end<=len(text) or not isinstance(replacement,str): raise ValueError("edit")
        normalized.append((start,end,replacement,index))
    deleted=sorted((s,e) for s,e,r,i in normalized if s<e)
    for a,b in zip(deleted,deleted[1:]):
        if a[1]>b[0]: raise ValueError("overlap")
    for s,e,r,i in normalized:
        if s==e and any(a<s<b for a,b in deleted): raise ValueError("inside")
    insertions={}; replacements={}
    for s,e,r,i in normalized:
        if s==e: insertions.setdefault(s,[]).append(r)
        else: replacements[s]=(e,r)
    pieces=[]; p=0
    while p<=len(text):
        pieces.extend(insertions.get(p,[]))
        if p in replacements:
            end,value=replacements[p]; pieces.append(value); p=end
        elif p<len(text): pieces.append(text[p]); p+=1
        else: break
    return "".join(pieces)
''',
     '''from solution import patch_text
class Check(unittest.TestCase):
    def test_original_coordinates(self):
        self.assertEqual(patch_text("abcdef",[(4,6,"Y"),(1,3,"X"),(1,1,"A"),(3,3,"B"),(1,1,"C")]),"aACXBdY")
        self.assertEqual(patch_text("",[(0,0,"a"),(0,0,"b")]),"ab")
    def test_random(self):
        import random
        rng=random.Random(111303)
        for _ in range(220):
            text="abcdefghijkl"; edits=[]; removals={}; inserts={}; p=0
            while p<len(text):
                if rng.random()<.3:
                    end=min(len(text),p+rng.randrange(1,4)); removals[p]=(end,str(p)); edits.append((p,end,str(p))); p=end
                else: p+=1
            legal=[p for p in range(len(text)+1) if not any(s<p<e for s,(e,r) in removals.items())]
            for _ in range(5):
                p=rng.choice(legal); value=rng.choice("XYZ"); edits.append((p,p,value))
            rng.shuffle(edits); old=edits[:]
            for s,e,r in edits:
                if s==e: inserts.setdefault(s,[]).append(r)
            expected=[]
            for p in range(len(text)+1):
                if any(s<p<e for s,(e,r) in removals.items()): continue
                expected.extend(inserts.get(p,[]))
                if p in removals: expected.append(removals[p][1])
                elif p<len(text) and not any(s<=p<e for s,(e,r) in removals.items()): expected.append(text[p])
            self.assertEqual(patch_text(text,edits),"".join(expected)); self.assertEqual(edits,old)
    def test_reject(self):
        for edits in [[(0,3,"a"),(2,4,"b")],[(0,3,"a"),(1,1,"b")],[(-1,0,"")],[(0,5,"")],[(0,1,2)],[(.0,1,"")]]:
            with self.assertRaises(ValueError): patch_text("abcd",edits)
''', {}, 'def patch_text(text,edits):\n'),
    ("cache_trace",
     "Implement cache_trace(capacity, operations), a pure simulation of a bounded cache. Call checked_capacity from helpers.py exactly once at entry, and use its returned value. Each operation is (time, action, key, value, ttl). All times are nonnegative integers and nondecreasing. Keys are strings. 'put' requires an integer value and nonnegative integer ttl; 'get' requires both value and ttl are None. Unknown actions and any invalid field raise ValueError, including in operations after capacity-zero puts. Before each operation, remove entries whose expiry<=time. A put replaces an existing key, makes it most recently used, and sets expiry=time+ttl. ttl=0 removes that key without adding it. With positive capacity, evict least recently used entries until within capacity. A get appends the cached value or None to a results list; a hit becomes most recently used. Capacity zero stores nothing. Return (results, final_values), where final_values is a new dictionary of key to value for the remaining entries; expiry and ordering are not exposed. Never mutate operations.",
     '''from helpers import checked_capacity
def cache_trace(capacity,operations):
    capacity=checked_capacity(capacity); cache={}; results=[]; previous=0
    for now,action,key,value,ttl in operations:
        if not isinstance(now,int) or now<previous or now<0 or not isinstance(key,str): raise ValueError("fields")
        previous=now
        if action=="put":
            if not isinstance(value,int) or not isinstance(ttl,int) or ttl<0: raise ValueError("put")
        elif action=="get":
            if value is not None or ttl is not None: raise ValueError("get")
        else: raise ValueError("action")
        for item in list(cache):
            if cache[item][1]<=now: del cache[item]
        if action=="get":
            entry=cache.pop(key,None); results.append(None if entry is None else entry[0])
            if entry is not None: cache[key]=entry
        else:
            cache.pop(key,None)
            if ttl and capacity:
                cache[key]=(value,now+ttl)
                while len(cache)>capacity: del cache[next(iter(cache))]
    return results,{key:value for key,(value,expiry) in cache.items()}
''',
     '''from solution import cache_trace
class Check(unittest.TestCase):
    def test_random_trace(self):
        import random
        rng=random.Random(111304)
        for capacity in range(5):
            for _ in range(45):
                entries={}; rank=[]; answer=[]; operations=[]; now=0
                for j in range(35):
                    now+=rng.randrange(3); key=rng.choice("abcd"); action=rng.choice(["put","get"])
                    value=rng.randrange(-5,6) if action=="put" else None; ttl=rng.randrange(7) if action=="put" else None
                    operations.append((now,action,key,value,ttl))
                    expired=[k for k in rank if entries[k][1]<=now]
                    for k in expired: rank.remove(k); del entries[k]
                    if action=="get":
                        answer.append(entries[key][0] if key in entries else None)
                        if key in entries: rank.remove(key); rank.append(key)
                    else:
                        if key in entries: rank.remove(key); del entries[key]
                        if ttl and capacity:
                            entries[key]=(value,now+ttl); rank.append(key)
                            if len(rank)>capacity: victim=rank.pop(0); del entries[victim]
                before=operations[:]
                self.assertEqual(cache_trace(capacity,operations),(answer,{k:v[0] for k,v in entries.items()}))
                self.assertEqual(operations,before)
    def test_validation(self):
        cases=[[(1,"put","a",1,1),(0,"get","a",None,None)],[(0,"x","a",None,None)],[(0,"get","a",1,None)],[(0,"put","a",1,-1)],[(0,"put",4,1,1)],[(0,"put","a",1.5,1)]]
        for operations in cases:
            with self.assertRaises(ValueError): cache_trace(0,operations)
        with self.assertRaises(ValueError): cache_trace(-1,[])
    def test_capacity_helper_result(self):
        import helpers,importlib,solution
        old=helpers.checked_capacity; seen=[]
        def capped(value): seen.append(value); old(value); return 1
        helpers.checked_capacity=capped
        try:
            importlib.reload(solution)
            answer=solution.cache_trace(3,[(0,"put","a",1,10),(0,"put","b",2,10),(1,"get","a",None,None)])
            self.assertEqual(answer,([None],{"b":2})); self.assertEqual(seen,[3])
        finally:
            helpers.checked_capacity=old
            importlib.reload(solution)
''',
     {"config.py": 'LIMIT=8\nLIMIT+=8\n', "helpers.py": 'from config import LIMIT\ndef checked_capacity(value):\n    if not isinstance(value,int) or not 0<=value<=LIMIT: raise ValueError("capacity")\n    return value\n'},
     'from helpers import checked_capacity\ndef cache_trace(capacity,operations):\n'),
]


def build_workflows(destination):
    if (destination / 'manifest.json').exists():
        raise ValueError('Choose a new destination; do not overwrite fixed evidence')
    cases = [(name, spec + PRESERVE, COMPAT + oracle, tests + COMMON_TEST, files)
             for name, spec, oracle, tests, files, declaration in TASKS]
    ids = build_suite(destination, cases, version=13)
    for name, spec, oracle, tests, files, declaration in TASKS:
        root = destination / 'repo_bundles' / name
        (root / 'solution.py').write_text(COMPAT + declaration + '    raise NotImplementedError("repair this function")\n', encoding='utf-8')
        path = destination / 'metadata' / f'{name}.json'
        meta = json.loads(path.read_text(encoding='utf-8'))
        meta['pinned_files'] = ['solution.py']
        meta['snapshot_sha256'] = digest_tree(root)
        meta['split'] = 'fresh synthetic workflow holdout before first model evaluation'
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    path = destination / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    manifest.update(constructed_unix=time.time(), generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    limitations='Four synthetic dictionary/string workflows, not real-repository patch coverage')
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', default='fixtures/workflow-holdout-v13b')
    args = parser.parse_args()
    print(build_workflows(Path(args.destination)))


if __name__ == '__main__':
    main()
