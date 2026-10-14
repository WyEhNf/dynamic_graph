import copy
import unittest
from solution import window_sums

class PublicContract(unittest.TestCase):

    def test_sums_sizes_and_input(self):
        values = [2, -1, 4, 0, 3]
        frozen = values[:]
        for size in (1, 2, 3, 5, 8):
            self.assertEqual(window_sums(values, size), [sum(values[i:i + size]) for i in range(max(0, len(values) - size + 1))])
            self.assertEqual(values, frozen)
        self.assertEqual(window_sums([], 1), [])
        for size in (0, -1):
            with self.assertRaises(ValueError):
                window_sums(values, size)
