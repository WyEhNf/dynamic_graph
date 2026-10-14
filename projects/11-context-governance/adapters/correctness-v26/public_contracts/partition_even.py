import copy
import unittest
import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_partition_order_duplicates_fresh_lists(self):
        values=[1,2,1,4,3]; frozen=values[:]
        with patch.object(solution,'is_even',side_effect=lambda value:value==1) as helper:
            even,other=solution.partition_even(values)
            self.assertEqual((even,other),([1,1],[2,4,3]))
            self.assertIsNot(even,values); self.assertIsNot(other,values); self.assertIsNot(even,other)
            self.assertEqual([c.args[0] for c in helper.call_args_list],values)
        self.assertEqual(values,frozen)
        self.assertEqual(solution.partition_even([]),([],[]))
