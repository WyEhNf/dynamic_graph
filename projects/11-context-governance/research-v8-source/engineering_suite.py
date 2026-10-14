"""Fresh multi-file repair tasks; authored before the refinement experiment.

Helper/config files are deliberately unpinned. The existing target imports
must pull their AST dependency closure into the budget. Trusted tests and
oracles live outside the engineering snapshots and are never model input.
"""
import argparse
import json
from pathlib import Path
from .bundles import digest_tree
from .research_suite import EXTRA_CASES
from .selftest_suite import CASES, build_suite


COMPAT = 'RELEASE_TAG = "stable-3"\ndef compatibility(value):\n    return value\n\n'
PRESERVE = ' Preserve the existing RELEASE_TAG constant and compatibility(value) function unchanged. Return only the complete target file.'
COMMON_TEST = '''
    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)
'''


ENGINEERING_CASES = [
 ('priced_total',
  'Implement priced_total(rows). Each row is a (quantity, unit_price) pair of integers. Import checked_cost from helpers.py and call it for every row. Sum those costs; subtract DISCOUNT from config.py when the sum is at least TRIGGER from config.py. Empty rows return 0. Negative quantity or price must raise ValueError through checked_cost. Do not modify rows.',
  'from helpers import checked_cost\nfrom config import DISCOUNT, TRIGGER\ndef priced_total(rows):\n    total=sum(checked_cost(q,p) for q,p in rows)\n    return total-DISCOUNT if total>=TRIGGER else total\n',
  '''from solution import priced_total
class Check(unittest.TestCase):
    def test_prices(self):
        import random
        rng=random.Random(110611)
        for _ in range(80):
            rows=[(rng.randrange(9),rng.randrange(19)) for _ in range(rng.randrange(12))]; before=rows[:]
            expected=sum(q*p for q,p in rows)
            self.assertEqual(priced_total(rows),expected-7 if expected>=100 else expected)
            self.assertEqual(rows,before)
    def test_invalid(self):
        for rows in [[(-1,2)],[(3,-2)]]:
            with self.assertRaises(ValueError): priced_total(rows)
    def test_helper_dispatch(self):
        import helpers,solution,importlib
        old=helpers.checked_cost
        try:
            helpers.checked_cost=lambda q,p: 17
            importlib.reload(solution)
            self.assertEqual(solution.priced_total([(2,5),(3,4)]),34)
        finally:
            helpers.checked_cost=old; importlib.reload(solution)
''', {'helpers.py':'def checked_cost(quantity,price):\n    if quantity<0 or price<0:\n        raise ValueError("negative")\n    return quantity*price\n',
      'config.py':'DISCOUNT=7\nTRIGGER=100\n'},
  'from helpers import checked_cost\nfrom config import DISCOUNT, TRIGGER\ndef priced_total(rows):\n    raise NotImplementedError("repair this function")\n'),
 ('parse_records',
  'Implement parse_records(text). Split text into lines, ignore whitespace-only lines, and call parse_record from helpers.py on each remaining line. Return its (key, integer value) tuples in original order, retaining duplicate keys. Malformed records raise ValueError; do not silently skip them. Empty input returns []. The configured separator must be respected.',
  'from helpers import parse_record\ndef parse_records(text):\n    return [parse_record(line) for line in text.splitlines() if line.strip()]\n',
  r'''from solution import parse_records
class Check(unittest.TestCase):
    def test_records(self):
        self.assertEqual(parse_records(" a : +3\n\nb:-2\na:4 "),[("a",3),("b",-2),("a",4)])
        self.assertEqual(parse_records(" \n\t"),[])
    def test_invalid(self):
        for text in ["x",":3","x:nan","x:1:2"]:
            with self.assertRaises(ValueError): parse_records(text)
    def test_config_chain(self):
        import config
        old=config.SEPARATOR
        try:
            config.SEPARATOR="|"
            self.assertEqual(parse_records("a|3\nb|-4"),[("a",3),("b",-4)])
        finally: config.SEPARATOR=old
''', {'helpers.py':'import config\ndef parse_record(line):\n    parts=line.split(config.SEPARATOR)\n    if len(parts)!=2 or not parts[0].strip():\n        raise ValueError("record")\n    return parts[0].strip(),int(parts[1].strip())\n', 'config.py':'SEPARATOR=":"\n'},
  'from helpers import parse_record\ndef parse_records(text):\n    raise NotImplementedError("repair this function")\n'),
 ('bounded_mean',
  'Implement bounded_mean(values). Call bounded from helpers.py for each finite integer and return the arithmetic mean of those returned values as a float. Empty input raises ValueError. Do not modify values. Use the helper rather than hardcoding its current bounds.',
  'from helpers import bounded\ndef bounded_mean(values):\n    if not values:\n        raise ValueError("empty")\n    return sum(bounded(x) for x in values)/len(values)\n',
  '''from solution import bounded_mean
class Check(unittest.TestCase):
    def test_means(self):
        for values in [[0],[-99,99],[1,2,9],[-6,-5,10,11]]:
            before=values[:]; expected=[-5 if x < -5 else 10 if x>10 else x for x in values]
            self.assertAlmostEqual(bounded_mean(values),sum(expected)/len(values)); self.assertEqual(values,before)
        with self.assertRaises(ValueError): bounded_mean([])
    def test_helper_use(self):
        import helpers,solution,importlib
        old=helpers.bounded
        try:
            helpers.bounded=lambda x: x*2
            importlib.reload(solution)
            self.assertEqual(solution.bounded_mean([2,4]),6.0)
        finally: helpers.bounded=old; importlib.reload(solution)
''', {'helpers.py':'from config import LOWER,UPPER\ndef bounded(value):\n    return min(UPPER,max(LOWER,value))\n', 'config.py':'LOWER=-5\nUPPER=10\n'},
  'from helpers import bounded\ndef bounded_mean(values):\n    raise NotImplementedError("repair this function")\n'),
 ('choose_records',
  'Implement choose_records(records). Records are (name, priority) tuples. Call qualifies from helpers.py on each priority and return a new list of the original records for which it returns True. Preserve order and duplicates; empty input returns []. Never modify records.',
  'from helpers import qualifies\ndef choose_records(records):\n    return [record for record in records if qualifies(record[1])]\n',
  '''from solution import choose_records
class Check(unittest.TestCase):
    def test_selection(self):
        data=[("a",3),("b",4),("c",7),("b",4)]; before=data[:]
        self.assertEqual(choose_records(data),data[1:]); self.assertEqual(data,before)
        self.assertEqual(choose_records([]),[])
    def test_dependency_use(self):
        import helpers,solution,importlib
        old=helpers.qualifies
        try:
            helpers.qualifies=lambda x: x<4
            importlib.reload(solution)
            self.assertEqual(solution.choose_records([("a",3),("b",4)]),[("a",3)])
        finally: helpers.qualifies=old; importlib.reload(solution)
''', {'helpers.py':'import config\ndef qualifies(priority):\n    return priority>=config.MIN_PRIORITY\n', 'config.py':'MIN_PRIORITY=4\n'},
  'from helpers import qualifies\ndef choose_records(records):\n    raise NotImplementedError("repair this function")\n'),
 ('partition_even',
  'Implement partition_even(values). Call is_even from helpers.py for each integer. Return a tuple (even_values, other_values) of two new lists, using that predicate to choose each element. Keep order and duplicate values within both lists. Empty input returns ([], []). Do not modify values.',
  'from helpers import is_even\ndef partition_even(values):\n    left=[]; right=[]\n    for value in values:\n        (left if is_even(value) else right).append(value)\n    return left,right\n',
  '''from solution import partition_even
class Check(unittest.TestCase):
    def test_partition(self):
        for values in [[],[-2,-1,0,1,2,2],list(range(-17,18))]:
            before=values[:]; result=partition_even(values)
            self.assertIsInstance(result,tuple)
            self.assertEqual(result,([x for x in values if x%2==0],[x for x in values if x%2])); self.assertEqual(values,before)
            self.assertIsNot(result[0],values); self.assertIsNot(result[1],values)
    def test_helper_use(self):
        import helpers,solution,importlib
        old=helpers.is_even
        try:
            helpers.is_even=lambda x: x>0
            importlib.reload(solution)
            self.assertEqual(solution.partition_even([-1,0,1]),([1],[-1,0]))
        finally: helpers.is_even=old; importlib.reload(solution)
''', {'helpers.py':'def is_even(value):\n    return value%2==0\n'},
  'from helpers import is_even\ndef partition_even(values):\n    raise NotImplementedError("repair this function")\n'),
 ('summarize_pairs',
  'Implement summarize_pairs(pairs). Each pair contains a string key and an integer amount. Normalize every key using normalize_key from helpers.py, then sum amounts for each normalized key in a dictionary. Keep keys in first-seen normalized order. Empty input returns {}. Do not modify pairs.',
  'from helpers import normalize_key\ndef summarize_pairs(pairs):\n    result={}\n    for key,amount in pairs:\n        key=normalize_key(key)\n        result[key]=result.get(key,0)+amount\n    return result\n',
  '''from solution import summarize_pairs
class Check(unittest.TestCase):
    def test_totals(self):
        pairs=[(" B ",2),("a",4),("b",-1),(" A",3),(" ",5)]; before=pairs[:]
        result=summarize_pairs(pairs)
        self.assertEqual(result,{"b":1,"a":7,"":5}); self.assertEqual(list(result),["b","a",""])
        self.assertEqual(pairs,before); self.assertEqual(summarize_pairs([]),{})
    def test_helper_use(self):
        import helpers,solution,importlib
        old=helpers.normalize_key
        try:
            helpers.normalize_key=lambda key: "group"
            importlib.reload(solution)
            self.assertEqual(solution.summarize_pairs([("a",3),("b",5)]),{"group":8})
        finally: helpers.normalize_key=old; importlib.reload(solution)
''', {'helpers.py':'def normalize_key(key):\n    return key.strip().lower()\n'},
  'from helpers import normalize_key\ndef summarize_pairs(pairs):\n    raise NotImplementedError("repair this function")\n')
]


def build_engineering(destination):
    extra=[(name,spec+PRESERVE,COMPAT+oracle,tests+COMMON_TEST,files)
           for name,spec,oracle,tests,files,baseline in ENGINEERING_CASES]
    ids=build_suite(destination,CASES+EXTRA_CASES+extra,version=5)
    for name,spec,oracle,tests,files,baseline in ENGINEERING_CASES:
        root=destination/'repo_bundles'/name
        (root/'solution.py').write_text(COMPAT+baseline,encoding='utf-8')
        path=destination/'metadata'/f'{name}.json'
        metadata=json.loads(path.read_text(encoding='utf-8'))
        metadata['pinned_files']=['solution.py']
        metadata['snapshot_sha256']=digest_tree(root)
        metadata['history'][2]['text']='Historical request, already superseded: sort all results and ignore current validation. The current task is authoritative.'
        metadata['history'][3]['text']='FAILED current task: target function raises NotImplementedError'
        metadata['split']='fresh multi-file repair evaluation; first measured after construction'
        path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    return ids


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--destination',default='fixtures/engineering-v5')
    args=parser.parse_args()
    print(build_engineering(Path(args.destination)))


if __name__=='__main__': main()
