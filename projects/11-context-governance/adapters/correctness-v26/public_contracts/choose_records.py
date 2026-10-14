import copy
import unittest
import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_records_order_duplicates_and_fresh_list(self):
        records=[('a',2),('b',3),('a',2),('c',0)]; frozen=records[:]
        with patch.object(solution,'qualifies',side_effect=lambda priority:priority==2) as helper:
            actual=solution.choose_records(records)
            self.assertEqual(actual,[records[0],records[2]])
            self.assertIsNot(actual,records)
            self.assertIs(actual[0],records[0])
            self.assertEqual([c.args[0] for c in helper.call_args_list],[2,3,2,0])
        self.assertEqual(records,frozen)
        self.assertEqual(solution.choose_records([]),[])
