import copy
import unittest
import solution

class PublicContract(unittest.TestCase):

    def test_round_order_surplus_empty_validation_and_input(self):
        for demands, total, expected in [([1, 4, 2], 5, [1, 2, 2]), ([3, 3, 3], 4, [2, 1, 1]), ([1, 0, 2], 20, [1, 0, 2]), ([], 5, []), ([2, 2], 0, [0, 0])]:
            frozen = demands[:]
            actual = solution.allocate_round_robin(demands, total)
            self.assertEqual(actual, expected)
            self.assertIsNot(actual, demands)
            self.assertEqual(demands, frozen)
        for demands, total in [([], -1), ([1, -1], 2), ([1, 1.5], 2), ([1], 2.5)]:
            with self.assertRaises(ValueError):
                solution.allocate_round_robin(demands, total)
