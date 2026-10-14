import copy
import unittest
from unittest.mock import patch
import solution

class PublicContract(unittest.TestCase):
    def test_lru_expiration_ttl_zero_and_no_mutation(self):
        operations = [(0,'put','a',1,10),(0,'put','b',2,1),(0,'get','a',None,None),(1,'get','b',None,None),(1,'put','c',3,8),(1,'put','d',4,8),(1,'get','a',None,None),(2,'put','c',9,0),(2,'get','c',None,None)]
        frozen = copy.deepcopy(operations)
        self.assertEqual(solution.cache_trace(2,operations), ([1,None,None,None], {'d':4}))
        self.assertEqual(operations, frozen)
        self.assertEqual(solution.cache_trace(0, [(0,'put','x',1,1),(0,'get','x',None,None)]), ([None],{}))

    def test_validate_fields_even_capacity_zero_and_helper_return(self):
        for operations in [[(1,'get','x',None,None),(0,'get','x',None,None)], [(0,'put','x','bad',1)], [(0,'put','x',1,-1)], [(0,'get','x',1,None)], [(0,'get',2,None,None)], [(0,'other','x',None,None)]]:
            with self.assertRaises(ValueError): solution.cache_trace(0, operations)
        with patch.object(solution, 'checked_capacity', return_value=0) as helper:
            self.assertEqual(solution.cache_trace(2, [(0,'put','x',1,2),(0,'get','x',None,None)]), ([None],{}))
            helper.assert_called_once_with(2)
