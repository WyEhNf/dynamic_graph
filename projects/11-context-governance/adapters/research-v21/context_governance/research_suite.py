"""Held-out semantics and multi-file tasks, authored before measuring v2."""
from pathlib import Path
from .selftest_suite import CASES, build_suite


EXTRA_CASES = [
 ('runs', 'Implement runs(values). Return a list of (value, count) tuples for consecutive equal values. Preserve run order. Empty input returns []. Never modify values.',
  'def runs(values):\n    result = []\n    for value in values:\n        if result and result[-1][0] == value:\n            result[-1] = (value, result[-1][1] + 1)\n        else:\n            result.append((value, 1))\n    return result\n',
  '''from solution import runs
class Check(unittest.TestCase):
    def test_runs(self):
        import random
        rng=random.Random(1181)
        for _ in range(150):
            values=[rng.choice([0,1,"a","b"]) for _ in range(rng.randrange(50))]; original=values[:]
            groups=runs(values)
            self.assertEqual([v for v,n in groups for _ in range(n)], original)
            self.assertTrue(all(n>0 for _,n in groups))
            self.assertTrue(all(groups[i][0]!=groups[i+1][0] for i in range(len(groups)-1)))
            self.assertEqual(values, original)
''', {}),
 ('rotate', 'Implement rotate(values, offset). Return a new list rotated right by integer offset. Negative offset rotates left. Offset may exceed length. Empty input returns []. Do not modify values.',
  'def rotate(values, offset):\n    if not values:\n        return []\n    k=offset % len(values)\n    return values[-k:] + values[:-k] if k else values[:]\n',
  '''from solution import rotate
class Check(unittest.TestCase):
    def test_rotation(self):
        for n in range(18):
            for offset in range(-40,41):
                values=list(range(n)); original=values[:]
                expected=[] if not n else [values[(i-offset)%n] for i in range(n)]
                actual=rotate(values,offset)
                self.assertEqual(actual,expected); self.assertEqual(values,original)
                self.assertIsNot(actual,values)
''', {}),
 ('intervals', 'Implement merge_intervals(intervals). Intervals are (start,end) integer pairs with start <= end. Return sorted tuples merging overlaps and touching endpoints. Empty input returns []. Invalid reversed intervals raise ValueError. Never mutate input.',
  'def merge_intervals(intervals):\n    if any(a>b for a,b in intervals):\n        raise ValueError("interval")\n    result=[]\n    for a,b in sorted(intervals):\n        if result and a<=result[-1][1]:\n            result[-1]=(result[-1][0],max(b,result[-1][1]))\n        else:\n            result.append((a,b))\n    return result\n',
  '''from solution import merge_intervals
class Check(unittest.TestCase):
    def test_examples(self):
        for values,expected in [([],[]), ([(4,8),(1,4)],[(1,8)]), ([(1,1),(2,3)],[(1,1),(2,3)]), ([(1,8),(2,3),(10,12)],[(1,8),(10,12)])]:
            original=values[:]; self.assertEqual(merge_intervals(values),expected); self.assertEqual(values,original)
    def test_invalid(self):
        with self.assertRaises(ValueError): merge_intervals([(4,2)])
    def test_half_integer_coverage(self):
        import random
        rng=random.Random(1183)
        for _ in range(150):
            pairs=[tuple(sorted((rng.randrange(-8,9),rng.randrange(-8,9)))) for _ in range(rng.randrange(15))]
            original=pairs[:]; merged=merge_intervals(pairs)
            coverage=lambda intervals: {p for a,b in intervals for p in range(2*a,2*b+1)}
            self.assertEqual(coverage(merged),coverage(original)); self.assertEqual(pairs,original)
            self.assertTrue(all(isinstance(x,tuple) and len(x)==2 and x[0]<=x[1] for x in merged))
            self.assertTrue(all(merged[i][1]<merged[i+1][0] for i in range(len(merged)-1)))
''', {}),
 ('normalize', 'Implement normalize_weights(weights). Import validate_nonnegative from helpers.py and use it to validate each weight. Return proportional floating-point weights summing to one. For empty input return []. All-zero nonempty input raises ValueError. Do not modify input.',
  'from helpers import validate_nonnegative\ndef normalize_weights(weights):\n    for weight in weights:\n        validate_nonnegative(weight)\n    if not weights:\n        return []\n    total=sum(weights)\n    if total==0:\n        raise ValueError("zero total")\n    return [x/total for x in weights]\n',
  '''from solution import normalize_weights
class Check(unittest.TestCase):
    def test_values(self):
        for values in [[],[1],[2,3,5],[0,1,0],[8,0,4]]:
            original=values[:]; result=normalize_weights(values)
            self.assertEqual(len(result),len(values)); self.assertEqual(values,original)
            for x,y in zip(result,values): self.assertAlmostEqual(x,y/sum(values))
    def test_invalid(self):
        for values in [[-1],[2,-1],[0],[0,0]]:
            with self.assertRaises(ValueError): normalize_weights(values)
    def test_validation_helper_used(self):
        import helpers,solution,importlib
        original=helpers.validate_nonnegative; calls=[]
        def track(value):
            calls.append(value); return original(value)
        try:
            helpers.validate_nonnegative=track; importlib.reload(solution)
            self.assertEqual(solution.normalize_weights([2,4]),[1/3,2/3]); self.assertEqual(calls,[2,4])
        finally:
            helpers.validate_nonnegative=original; importlib.reload(solution)
''', {'helpers.py':'def validate_nonnegative(value):\n    if value < 0:\n        raise ValueError("negative")\n'}),
 ('histogram', 'Implement histogram(values). Return a dictionary mapping each hashable value to its occurrence count. Empty input returns {}. Keep keys in first-seen order. Do not modify values.',
  'def histogram(values):\n    result={}\n    for value in values:\n        result[value]=result.get(value,0)+1\n    return result\n',
  '''from solution import histogram
class Check(unittest.TestCase):
    def test_counts(self):
        import random
        rng=random.Random(1185)
        for _ in range(120):
            values=[rng.choice([1,2,"x","y"]) for _ in range(rng.randrange(35))]; original=values[:]
            result=histogram(values)
            self.assertEqual(list(result),list(dict.fromkeys(values)))
            self.assertEqual(result,{x:values.count(x) for x in values}); self.assertEqual(values,original)
''', {}),
 ('prefix', 'Implement common_prefix(words). Return the longest common prefix of strings in words. Empty list returns empty string. Comparison is case sensitive and supports Unicode. Do not modify words.',
  'def common_prefix(words):\n    if not words:\n        return ""\n    prefix=words[0]\n    for word in words[1:]:\n        while not word.startswith(prefix):\n            prefix=prefix[:-1]\n    return prefix\n',
  '''from solution import common_prefix
class Check(unittest.TestCase):
    def test_prefix(self):
        for words,expected in [([],""),(["flower","flow","flight"],"fl"),(["ab","AB"],""),(["中文甲","中文乙"],"中文"),(["a",""],""),(["same"],"same")]:
            original=words[:]; self.assertEqual(common_prefix(words),expected); self.assertEqual(words,original)
''', {}),
 ('window', 'Implement window_sums(values, size). Return sums of consecutive full windows of length size. Size must be positive, otherwise raise ValueError. Size exceeding input length returns []. Do not modify input.',
  'def window_sums(values,size):\n    if size<=0:\n        raise ValueError("size")\n    if size>len(values):\n        return []\n    total=sum(values[:size]); result=[total]\n    for i in range(size,len(values)):\n        total+=values[i]-values[i-size]; result.append(total)\n    return result\n',
  '''from solution import window_sums
class Check(unittest.TestCase):
    def test_windows(self):
        for n in range(20):
            values=[i%5-2 for i in range(n)]; original=values[:]
            for size in range(1,23): self.assertEqual(window_sums(values,size),[sum(values[i:i+size]) for i in range(n-size+1)])
            self.assertEqual(values,original)
    def test_invalid(self):
        for size in [0,-2]:
            with self.assertRaises(ValueError): window_sums([1,2],size)
''', {}),
 ('threshold', 'Implement accepted(values). Import LIMIT from config.py. Return values meeting the configured threshold, preserving order. Use inclusive(value, LIMIT) from helpers.py to decide acceptance. Empty input returns []. Do not modify input.',
  'from config import LIMIT\nfrom helpers import inclusive\ndef accepted(values):\n    return [x for x in values if inclusive(x,LIMIT)]\n',
  '''from solution import accepted
class Check(unittest.TestCase):
    def test_threshold(self):
        values=list(range(-10,20)); original=values[:]
        self.assertEqual(accepted(values),[x for x in values if x>=7]); self.assertEqual(values,original); self.assertEqual(accepted([]),[])
    def test_dependency(self):
        import config,solution,importlib
        original=config.LIMIT
        try:
            for threshold in [-4,3,12]:
                config.LIMIT=threshold; importlib.reload(solution)
                self.assertEqual(solution.accepted(list(range(-10,20))),[x for x in range(-10,20) if x>=threshold])
        finally:
            config.LIMIT=original; importlib.reload(solution)
    def test_helper_used(self):
        import helpers,solution,importlib
        original=helpers.inclusive
        try:
            helpers.inclusive=lambda value,threshold: value < threshold
            importlib.reload(solution)
            self.assertEqual(solution.accepted(list(range(12))),list(range(7)))
        finally:
            helpers.inclusive=original; importlib.reload(solution)
''', {'config.py':'LIMIT = 7\n','helpers.py':'def inclusive(value, threshold):\n    return value >= threshold\n'})
]


def main():
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--destination',default='fixtures/research-v3')
    args=parser.parse_args()
    print(build_suite(Path(args.destination), CASES + EXTRA_CASES, version=4))


if __name__=='__main__': main()
