import copy
import random
import unittest
from unittest.mock import patch
import solution

class PublicContract(unittest.TestCase):

    def test_validation_includes_explicit_zero_and_helpers(self):
        for left, right, rows, inner, cols in [({(2, 0): 0}, {}, 2, 2, 2), ({}, {(0, 2): 0}, 2, 2, 2), ({}, {}, -1, 2, 2)]:
            with self.assertRaises(ValueError):
                solution.sparse_product(left, right, rows, inner, cols)
        self.assertEqual(solution.sparse_product({}, {}, 0, 0, 0), {})
        with patch.object(solution, 'checked_size', wraps=solution.checked_size) as size, patch.object(solution, 'checked_vertex', wraps=solution.checked_vertex) as vertex:
            self.assertEqual(solution.sparse_product({(1, 0): 0}, {(0, 1): 0}, 2, 1, 2), {})
            self.assertGreaterEqual(len(size.call_args_list), 3)
            for args in [(1, 2), (0, 1), (0, 1), (1, 2)]:
                self.assertTrue(any((c.args == args for c in vertex.call_args_list)))

    def test_small_dense_definition_and_immutability(self):
        rng = random.Random(260110)
        for _ in range(40):
            rows, inner, cols = [rng.randrange(1, 5) for _ in range(3)]
            left = {(i, k): rng.randrange(-2, 3) for i in range(rows) for k in range(inner) if rng.randrange(2)}
            right = {(k, j): rng.randrange(-2, 3) for k in range(inner) for j in range(cols) if rng.randrange(2)}
            frozen = copy.deepcopy((left, right))
            result = solution.sparse_product(left, right, rows, inner, cols)
            expected = {(i, j): sum((left.get((i, k), 0) * right.get((k, j), 0) for k in range(inner))) for i in range(rows) for j in range(cols)}
            self.assertEqual(result, {key: value for key, value in expected.items() if value})
            self.assertEqual((left, right), frozen)
