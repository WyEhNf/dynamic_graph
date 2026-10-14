import copy
import unittest
import solution

class PublicContract(unittest.TestCase):

    def test_duplicates_scalar_values_order_and_empties(self):
        left = [('b', 1), ('a', 2), ('b', 3)]
        right = [('b', 10), ('c', 11), ('b', 12), ('c', 13)]
        frozen = copy.deepcopy((left, right))
        self.assertEqual(solution.outer_join(left, right), [('b', 1, 10), ('b', 1, 12), ('a', 2, None), ('b', 3, 10), ('b', 3, 12), ('c', None, 11), ('c', None, 13)])
        self.assertEqual((left, right), frozen)
        self.assertEqual(solution.outer_join([], right), [(k, None, v) for k, v in right])
        self.assertEqual(solution.outer_join(left, []), [(k, v, None) for k, v in left])
        self.assertEqual(solution.outer_join([], []), [])

    def test_fresh_result_and_public_exports(self):
        values = [('x', {'nested': 1})]
        result = solution.outer_join(values, [])
        self.assertIsNot(result, values)
        self.assertEqual(solution.RELEASE_TAG, 'stable-3')
        marker = object()
        self.assertIs(solution.compatibility(marker), marker)
