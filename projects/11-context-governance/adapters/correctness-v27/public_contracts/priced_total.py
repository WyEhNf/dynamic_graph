from collections import Counter
import copy
import unittest
import solution
import config
from unittest.mock import patch

class PublicContract(unittest.TestCase):

    def test_helper_cost_and_configured_discount_and_input(self):
        rows = [(1, 2), (3, 4)]
        frozen = rows[:]
        with patch.object(solution, 'checked_cost', side_effect=lambda quantity, price: config.TRIGGER) as helper:
            self.assertEqual(solution.priced_total(rows), 2 * config.TRIGGER - config.DISCOUNT)
            self.assertFalse(Counter(rows) - Counter([c.args for c in helper.call_args_list]))
        self.assertEqual(rows, frozen)
        self.assertEqual(solution.priced_total([]), 0)
        with self.assertRaises(ValueError):
            solution.priced_total([(-1, 2)])
