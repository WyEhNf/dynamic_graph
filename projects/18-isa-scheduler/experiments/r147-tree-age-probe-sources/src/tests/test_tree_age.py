from dataclasses import replace
import unittest

from isa_scheduler.model import parse_block, BudgetExceeded, InfeasibleSchedule
from isa_scheduler.tree_age import schedule_tree_age
from scripts.research_spine_age_probe import check
from scripts.tree_raw_oracles import dfs_deadline_optimum, raw_optimum
from tests.test_retention_search import raw


class TreeAgeTests(unittest.TestCase):
    def test_ordered_duplicate_unused_and_four_widths(self):
        rows = [('GET', (), 'unused'), ('GET', (), 'a'), ('GET', (), 'b'),
                ('ADD', (1, 1), None), ('MULW', (2, 2), None), ('ADD', (4, 3), None),
                ('MULW', (5, 5), None), ('SET', (6,), 'out')]
        for bits in (2, 3, 4, 5):
            data = raw(rows, bits); candidate = schedule_tree_age(parse_block(data))
            check(data, candidate, candidate['stats']['original_order'])
            self.assertEqual(candidate['stats']['inserted_copy_count'], dfs_deadline_optimum(data)['copies'])
            self.assertEqual(candidate['stats']['tree_age']['truncated_outcomes'], 0)

    def test_age_context_and_exhaustive_family(self):
        rows = [('GET', (), f'r{i}') for i in range(4)]
        rows += [('ADD', (0, 1), None), ('MULW', (2, 2), None), ('ADD', (5, 5), None),
                 ('MULW', (6, 6), None), ('ADD', (7, 7), None), ('ADD', (8, 3), None),
                 ('MULW', (4, 9), None), ('SET', (10,), 'out')]
        data = raw(rows); candidate = schedule_tree_age(parse_block(data), max_outcomes=1024)
        check(data, candidate, candidate['stats']['original_order'])
        self.assertEqual(candidate['stats']['inserted_copy_count'], dfs_deadline_optimum(data)['copies'])
        exact = raw_optimum(data)
        if exact['status'] == 'optimal_under_identity_model':
            self.assertGreaterEqual(candidate['stats']['inserted_copy_count'], exact['copies'])

    def test_hazard_shared_copy_and_dead_arithmetic_rejected(self):
        cases = [[('GET', (), 'a'), ('ADD', (0, 0), None), ('SET', (1,), 'a')],
                 [('GET', (), 'a'), ('ADD', (0, 0), None), ('MULW', (0, 1), None), ('SET', (2,), 'out')],
                 [('GET', (), 'a'), ('ADD', (0, 0), None)]]
        for rows in cases:
            with self.assertRaises(ValueError): schedule_tree_age(parse_block(raw(rows)))
        data = {'block_id': 'copy', 'bit_width': 2, 'instructions': [
            {'id': 0, 'op': 'GET', 'reg': 'a'}, {'id': 1, 'op': 'COPY', 'source': 't#1'},
            {'id': 2, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]}
        with self.assertRaises(ValueError): schedule_tree_age(parse_block(data))

    def test_budget_and_depth_are_unknown_not_proof(self):
        data = raw([('GET', (), 'a'), ('GET', (), 'b'), ('ADD', (0, 1), None), ('SET', (2,), 'out')])
        block = parse_block(data)
        with self.assertRaises(BudgetExceeded): schedule_tree_age(block, max_states=1)
        with self.assertRaises(BudgetExceeded): schedule_tree_age(block, time_budget_ms=1e-9)
        with self.assertRaises(ValueError): schedule_tree_age(block, max_depth=1)
        with self.assertRaises(ValueError): schedule_tree_age(replace(block, bit_width=0))
        self.assertEqual(raw_optimum(data, max_states=1)['status'], 'unknown_budget')

    def test_direct_w2_and_multiple_output_roots(self):
        data = raw([('GET', (), 'a'), ('MULW', (0, 0), None), ('SET', (1,), 'out'),
                    ('GET', (), 'unused'), ('GET', (), 'b'), ('ADD', (4, 4), None), ('SET', (5,), 'out2')])
        candidate = schedule_tree_age(replace(parse_block(data), bit_width=1))
        check(data, candidate, candidate['stats']['original_order'])
        self.assertEqual(candidate['stats']['inserted_copy_count'], 0)


if __name__ == '__main__': unittest.main()
