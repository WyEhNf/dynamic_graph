import copy
import unittest
import solution
from unittest.mock import patch

class PublicContract(unittest.TestCase):

    def test_layers_duplicates_cycles_unreachable_validation_and_input(self):
        edges = [(0, 2), (0, 1), (2, 3), (1, 3), (3, 0), (0, 2)]
        frozen = edges[:]
        self.assertEqual(solution.shortest_layers(5, edges, 0), [[0], [1, 2], [3]])
        self.assertEqual(edges, frozen)
        for n, edges, start in [(5, [(4, 5)], 0), (2, [], 2), (-1, [], 0)]:
            with self.assertRaises(ValueError):
                solution.shortest_layers(n, edges, start)
        with patch.object(solution, 'checked_size', wraps=solution.checked_size) as size, patch.object(solution, 'checked_vertex', wraps=solution.checked_vertex) as vertex:
            self.assertEqual(solution.shortest_layers(3, [(1, 2)], 0), [[0]])
            self.assertTrue(size.called)
            for endpoint in (0, 1, 2):
                self.assertTrue(any((c.args == (endpoint, 3) for c in vertex.call_args_list)))
