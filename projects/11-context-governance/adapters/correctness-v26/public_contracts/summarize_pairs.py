import copy
import unittest
import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_normalized_order_sums_and_input(self):
        pairs=[(' B ',2),('a',3),('b',4),(' A',-1)]; frozen=pairs[:]
        with patch.object(solution,'normalize_key',side_effect=lambda key:key.strip().lower()) as helper:
            actual=solution.summarize_pairs(pairs)
            self.assertEqual(actual,{'b':6,'a':2})
            self.assertEqual(list(actual),['b','a'])
            self.assertEqual([c.args[0] for c in helper.call_args_list],[key for key,value in pairs])
        self.assertEqual(pairs,frozen)
        self.assertEqual(solution.summarize_pairs([]),{})
