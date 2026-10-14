import copy
import unittest
from solution import histogram
class PublicContract(unittest.TestCase):
    def test_counts_first_seen_and_input(self):
        values=['b',2,'b',1,2,'a']; frozen=copy.deepcopy(values)
        actual=histogram(values)
        self.assertEqual(actual,{'b':2,2:2,1:1,'a':1})
        self.assertEqual(list(actual),['b',2,1,'a'])
        self.assertEqual(values,frozen)
        self.assertEqual(histogram([]),{})
