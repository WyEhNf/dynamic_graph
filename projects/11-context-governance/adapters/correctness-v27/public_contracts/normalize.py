from collections import Counter
import copy
import unittest
from unittest.mock import patch
import solution

class PublicContract(unittest.TestCase):

    def test_public_values_and_validation(self):
        self.assertEqual(solution.normalize_weights([]), [])
        self.assertEqual(solution.normalize_weights([1, 3]), [0.25, 0.75])
        for values in ([0, 0], [1, -1], [0, -1, 2]):
            with self.assertRaises(ValueError):
                solution.normalize_weights(values)

    def test_helper_scaling_and_no_mutation(self):
        for values in ([0, 1, 2], [5], [4, 2, 4, 0]):
            frozen = copy.deepcopy(values)
            with patch.object(solution, 'validate_nonnegative', wraps=solution.validate_nonnegative) as helper:
                actual = solution.normalize_weights(values)
                self.assertFalse(Counter(values) - Counter([c.args[0] for c in helper.call_args_list]))
            self.assertEqual(values, frozen)
            self.assertAlmostEqual(sum(actual), 1.0)
            self.assertEqual(actual, solution.normalize_weights([3 * x for x in values]))
            for value, fraction in zip(values, actual):
                self.assertAlmostEqual(fraction, value / sum(values))
