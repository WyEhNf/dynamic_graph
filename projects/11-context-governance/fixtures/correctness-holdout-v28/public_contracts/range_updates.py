import copy
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
