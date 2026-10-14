from collections import Counter
import copy
import unittest
import solution
from unittest.mock import patch

class PublicContract(unittest.TestCase):

    def test_helper_return_controls_mean_and_input(self):
        values = [-9, 2, 80]
        frozen = values[:]
        with patch.object(solution, 'bounded', side_effect=lambda value: 2 * value + 1) as helper:
            actual = solution.bounded_mean(values)
            self.assertIsInstance(actual, float)
            self.assertAlmostEqual(actual, sum((2 * v + 1 for v in values)) / len(values))
            self.assertFalse(Counter(values) - Counter([c.args[0] for c in helper.call_args_list]))
        self.assertEqual(values, frozen)
        with self.assertRaises(ValueError):
            solution.bounded_mean([])
