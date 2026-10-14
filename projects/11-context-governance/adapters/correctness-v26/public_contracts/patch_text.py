import copy
import unittest
import solution

class PublicContract(unittest.TestCase):
    def test_original_coordinates_insert_order_and_endpoints(self):
        edits = [(1,3,'LONG'), (1,1,'A'), (1,1,'B'), (3,3,'C'), (5,6,'Z')]
        frozen = copy.deepcopy(edits)
        self.assertEqual(solution.patch_text('abcdef', edits), 'aABLONGCdeZ')
        self.assertEqual(edits, frozen)
        self.assertEqual(solution.patch_text('abc', [(1,2,'X')]), 'aXc')
        self.assertEqual(solution.patch_text('', [(0,0,'a'),(0,0,'b')]), 'ab')
        self.assertEqual(solution.patch_text('abc', []), 'abc')

    def test_invalid_overlap_and_types(self):
        for edits in [[(0,2,'x'),(1,3,'y')], [(0,3,'x'),(1,1,'y')], [(-1,0,'')], [(0,4,'')], [(2,1,'')], [(0,0,1)], [(0.5,1,'')]]:
            with self.assertRaises(ValueError): solution.patch_text('abc', edits)
        self.assertEqual(solution.patch_text('abcd', [(0,1,'X'),(3,4,'Y')]), solution.patch_text('abcd',[(3,4,'Y'),(0,1,'X')]))
