import copy
import unittest
from solution import stable_unique
class PublicContract(unittest.TestCase):
    def test_first_seen_order_and_input(self):
        values=[3,'a',1,3,'a',2,'b',1]; frozen=copy.deepcopy(values)
        actual=stable_unique(values)
        self.assertEqual(actual,[3,'a',1,2,'b'])
        self.assertEqual(values,frozen)
        self.assertEqual(stable_unique([]),[])
        self.assertEqual(stable_unique(actual),actual)
