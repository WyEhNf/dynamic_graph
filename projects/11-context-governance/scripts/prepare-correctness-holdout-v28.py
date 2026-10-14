"""Freeze two new algorithmic tasks before any v28 model candidate generation.

These are limited self-created holdout tasks. Once their evaluation outcomes
drive changes, they become DEV. Reference code is only for offline test validity.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'adapters'/'research-v24'))
from context_governance.bundles import digest_tree
from context_governance.quality import check_code

TASKS={
'wildcard_match':{
'spec':"Implement wildcard_match(text, pattern). Both inputs must be strings; otherwise raise ValueError. Match the entire text using case-sensitive Unicode code points. In pattern, '?' matches exactly one code point and '*' matches any sequence of zero or more code points; every other character is literal. Consecutive '*' characters have the same meaning as one '*'. There is no escape syntax. Return a bool. Empty text and/or pattern obey these same rules. Return only the complete solution.py file.",
'target':"def wildcard_match(text, pattern):\n    raise NotImplementedError('implement public requirements')\n",
'reference':'''def wildcard_match(text, pattern):
    if not isinstance(text,str) or not isinstance(pattern,str): raise ValueError('strings')
    row=[True]+[False]*len(text)
    for char in pattern:
        current=[False]*(len(text)+1)
        if char=='*':
            current[0]=row[0]
            for i in range(1,len(text)+1): current[i]=row[i] or current[i-1]
        else:
            for i in range(1,len(text)+1): current[i]=row[i-1] and (char=='?' or char==text[i-1])
        row=current
    return bool(row[-1])
''',
'public':'''import unittest
from solution import wildcard_match
class PublicContract(unittest.TestCase):
    def test_declared_pattern_semantics(self):
        for text,pattern,expected in [('ab','a?',True),('abc','a*c',True),('abc','a',False),('','**',True),('中a','?a',True),('a.b','a.b',True)]:
            self.assertIs(wildcard_match(text,pattern),expected)
        with self.assertRaises(ValueError): wildcard_match(None,'*')
''',
'tests':'''import itertools
import unittest
from solution import wildcard_match
def words(alphabet,maximum):
    return [''.join(chars) for n in range(maximum+1) for chars in itertools.product(alphabet,repeat=n)]
def enumerative_match(text,pattern):
    # Independent exhaustive split choices, not the reference's DP algorithm.
    if not pattern: return not text
    head=pattern[0]
    if head=='*': return any(enumerative_match(text[k:],pattern[1:]) for k in range(len(text)+1))
    return bool(text) and (head=='?' or head==text[0]) and enumerative_match(text[1:],pattern[1:])
class Evaluation(unittest.TestCase):
    def test_exhaustive_small_strings_patterns(self):
        for text in words('ab',4):
            for pattern in words('ab?*',4):
                self.assertIs(wildcard_match(text,pattern),bool(enumerative_match(text,pattern)))
    def test_unicode_literals_anchors_types_and_empty(self):
        for text,pattern in [('中🙂a','?*a'),('a[b].c','a[b].c'),('abc','*b*'),('','?'),('a',''),('abc','**a**c**'),('中中','中?')]:
            self.assertIs(wildcard_match(text,pattern),bool(enumerative_match(text,pattern)))
        for text,pattern in [(1,'*'),('a',None),([],''),('',{})]:
            with self.assertRaises(ValueError): wildcard_match(text,pattern)
''',
},
'range_updates':{
'spec':"Implement range_updates(values, operations). values is a list of integers. Every operation is a tuple (start, end, delta), where start/end/delta are integers and 0 <= start <= end <= len(values). Each operation adds delta to the half-open slice values[start:end]. Apply operations cumulatively and return a new list. Validate all input values and every operation before producing an answer; any invalid value, coordinate, or delta raises ValueError, including zero-length updates. Empty lists and empty operations obey the same validation rules. Never mutate values or operations, even on failure. Return only the complete solution.py file.",
'target':"def range_updates(values, operations):\n    raise NotImplementedError('implement public requirements')\n",
'reference':'''def range_updates(values, operations):
    if any(not isinstance(value,int) for value in values): raise ValueError('values')
    for start,end,delta in operations:
        if not all(isinstance(x,int) for x in (start,end,delta)) or not 0<=start<=end<=len(values): raise ValueError('operation')
    diff=[0]*(len(values)+1)
    for start,end,delta in operations:
        diff[start]+=delta
        diff[end]-=delta
    running=0
    result=[]
    for i,value in enumerate(values):
        running+=diff[i]
        result.append(value+running)
    return result
''',
'public':'''import copy
import unittest
from solution import range_updates
class PublicContract(unittest.TestCase):
    def test_half_open_cumulative_fresh_and_validation(self):
        values=[1,2,3]; operations=[(0,2,4),(1,3,-1)]; frozen=copy.deepcopy((values,operations))
        result=range_updates(values,operations)
        self.assertEqual(result,[5,5,2]); self.assertIsNot(result,values)
        self.assertEqual((values,operations),frozen)
        self.assertEqual(range_updates([],[(0,0,2)]),[])
        with self.assertRaises(ValueError): range_updates([1],[(1,1,'bad')])
''',
'tests':'''import copy
import itertools
import random
import unittest
from solution import range_updates
def definition(values,operations):
    return [value+sum(delta for start,end,delta in operations if start<=i<end) for i,value in enumerate(values)]
class Evaluation(unittest.TestCase):
    def test_exhaustive_small_two_update_sequences(self):
        for n in range(4):
            values=list(range(n))
            updates=[(a,b,d) for a in range(n+1) for b in range(a,n+1) for d in (-2,0,3)]
            for ops in itertools.product(updates,repeat=2):
                operations=list(ops); frozen=copy.deepcopy((values,operations))
                result=range_updates(values,operations)
                self.assertEqual(result,definition(values,operations))
                self.assertIsNot(result,values)
                self.assertEqual((values,operations),frozen)
    def test_seeded_larger_updates_and_failed_atomicity(self):
        rng=random.Random(260128)
        for _ in range(80):
            n=rng.randrange(15); values=[rng.randrange(-20,21) for _ in range(n)]
            operations=[]
            for _ in range(10):
                a,b=sorted((rng.randrange(n+1),rng.randrange(n+1)))
                operations.append((a,b,rng.randrange(-5,6)))
            self.assertEqual(range_updates(values,operations),definition(values,operations))
        for values,operations in [([1,'bad'],[]),([1],[(0,1,2),(1,1,'bad')]),([1],[(0,2,1)]),([1],[(1,0,1)]),([1],[(0.5,1,1)]),([],[(-1,0,1)])]:
            frozen=copy.deepcopy((values,operations))
            with self.assertRaises(ValueError): range_updates(values,operations)
            self.assertEqual((values,operations),frozen)
''',
}}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    destination=ROOT/'fixtures'/'correctness-holdout-v28'
    if destination.exists(): raise ValueError('refuse rewriting frozen independent tasks')
    start=time.perf_counter()
    for name in ('spec','metadata','repo_bundles','tests','oracle','public_contracts'):
        (destination/name).mkdir(parents=True)
    evidence=[]
    for case_id,task in TASKS.items():
        repo=destination/'repo_bundles'/case_id
        repo.mkdir()
        (repo/'solution.py').write_text(task['target'],encoding='utf-8')
        for index in range(3):
            (repo/f'unrelated_{index}.py').write_text(f'def unrelated_{index}(items):\n    return [value + {index} for value in items]\n',encoding='utf-8')
        (destination/'spec'/f'{case_id}.md').write_text(task['spec'],encoding='utf-8')
        (destination/'tests'/f'{case_id}.py').write_text(task['tests'],encoding='utf-8')
        (destination/'oracle'/f'{case_id}.py').write_text(task['reference'],encoding='utf-8')
        (destination/'public_contracts'/f'{case_id}.py').write_text(task['public'],encoding='utf-8')
        metadata={'origin':'Self-created independent new task; not official benchmark',
                  'case_id':case_id,'baseline_bundle':case_id,'snapshot_sha256':digest_tree(repo),
                  'target_file':'solution.py','pinned_files':['solution.py'],'history':[],
                  'dependencies':{'python':'>=3.12','external':[]}}
        (destination/'metadata'/f'{case_id}.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        public=check_code(task['reference'],repo,'solution.py',destination/'public_contracts'/f'{case_id}.py')
        evaluation=check_code(task['reference'],repo,'solution.py',destination/'tests'/f'{case_id}.py')
        placeholder=check_code(task['target'],repo,'solution.py',destination/'tests'/f'{case_id}.py')
        if not public['passed'] or not evaluation['passed'] or placeholder['passed']: raise RuntimeError(f'Invalid holdout contract: {case_id}')
        evidence.append({'id':case_id,'reference_public_pass':public['passed'],'reference_evaluation_pass':evaluation['passed'],
                         'placeholder_refused':not placeholder['passed'],'evaluation_methods':evaluation['tests_run']})
    manifest={'version':'correctness-holdout-v28','case_ids':list(TASKS),
              'origin':'Two self-created algorithmic tasks first frozen after v27 contracts and before any model generation on these tasks',
              'scope':'New finite task coverage only, not arbitrary-input proof or official score',
              'evaluation_policy':'Tests/oracle not used for prompt, repair or candidate selection; once evaluation outcomes influence changes this set becomes DEV',
              'script_sha256':sha(Path(__file__)),'prepared_unix':time.time(),
              'files_sha256':{p.relative_to(destination).as_posix():sha(p) for p in sorted(destination.rglob('*')) if p.is_file()}}
    (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'manifest_sha256':sha(destination/'manifest.json'),'cpu_only':True,'model_calls':0,'cases':evidence,
            'preparation_seconds':time.perf_counter()-start}
    (ROOT/'artifacts'/'correctness-holdout-v28-preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__': main()
