import copy
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
