import copy
import itertools
import unittest
from unittest.mock import patch
import solution

class PublicContract(unittest.TestCase):
    def test_cycle_invalid_empty_and_exports(self):
        self.assertEqual(solution.RELEASE_TAG, 'stable-3')
        marker = object()
        self.assertIs(solution.compatibility(marker), marker)
        self.assertEqual(solution.stable_topology(0, []), [])
        for n, edges in [(2, [(0,1),(1,0)]), (1, [(0,0)]), (2, [(0,2)]), (-1, [])]:
            with self.assertRaises(ValueError): solution.stable_topology(n, edges)

    def test_small_graph_exhaustion_and_helpers(self):
        # All 64 edge subsets between distinct vertices of a three-vertex graph.
        arcs = [(a,b) for a in range(3) for b in range(3) if a != b]
        for mask in range(1 << len(arcs)):
            edges = [arc for i, arc in enumerate(arcs) if mask & (1 << i)]
            frozen = copy.deepcopy(edges)
            valid = [list(order) for order in itertools.permutations(range(3))
                     if all(order.index(a) < order.index(b) for a,b in edges)]
            if not valid:
                with self.assertRaises(ValueError): solution.stable_topology(3, edges)
            else:
                # Lexicographically smallest topological order equals repeatedly choosing smallest available.
                self.assertEqual(solution.stable_topology(3, edges), min(valid))
            self.assertEqual(edges, frozen)
        edges = [(0,2), (0,2), (1,2)]
        with patch.object(solution, 'checked_size', wraps=solution.checked_size) as size, patch.object(solution, 'checked_vertex', wraps=solution.checked_vertex) as vertex:
            self.assertEqual(solution.stable_topology(3, edges), [0,1,2])
            self.assertTrue(any(c.args == (3,) for c in size.call_args_list))
            for endpoint in [0, 1, 2]: self.assertTrue(any(c.args == (endpoint,3) for c in vertex.call_args_list))
