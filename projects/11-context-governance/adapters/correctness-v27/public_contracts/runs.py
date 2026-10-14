import copy
import unittest
from solution import runs

class PublicContract(unittest.TestCase):

    def test_consecutive_runs_and_input(self):
        values = [3, 3, 1, 3, 2, 2]
        frozen = values[:]
        actual = runs(values)
        self.assertEqual(actual, [(3, 2), (1, 1), (3, 1), (2, 2)])
        self.assertEqual([v for v, n in actual for _ in range(n)], values)
        self.assertEqual(values, frozen)
        self.assertEqual(runs([]), [])
