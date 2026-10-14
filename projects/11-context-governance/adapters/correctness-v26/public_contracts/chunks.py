import copy
import unittest
from solution import chunks
class PublicContract(unittest.TestCase):
    def test_partition_order_size_and_no_mutation(self):
        for values in ([],[1],[3,1,3,2,4]):
            for size in (1,2,3,8):
                frozen=copy.deepcopy(values); actual=chunks(values,size)
                self.assertEqual([x for part in actual for x in part],values)
                self.assertTrue(all(0<len(part)<=size for part in actual))
                self.assertTrue(all(len(part)==size for part in actual[:-1]))
                self.assertEqual(values,frozen)
        for size in (0,-2):
            with self.assertRaises(ValueError): chunks([],size)
