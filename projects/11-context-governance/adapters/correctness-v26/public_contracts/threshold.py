import copy
import unittest
import solution
import config
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_controls_predicate_and_no_mutation(self):
        values=[2,8,2,-1]; frozen=values[:]
        with patch.object(solution,'inclusive',side_effect=lambda value,limit:value==2) as helper:
            self.assertEqual(solution.accepted(values),[2,2])
            self.assertEqual([c.args for c in helper.call_args_list],[(v,config.LIMIT) for v in values])
        self.assertEqual(values,frozen)
        self.assertEqual(solution.accepted([]),[])
