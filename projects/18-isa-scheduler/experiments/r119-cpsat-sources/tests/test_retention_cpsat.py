import importlib.util
import unittest

from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule, parse_block
from isa_scheduler.retention_cpsat import solve_retention_cpsat, schedule_retention_cpsat
from tests import test_retention_search as retention_tests

raw = retention_tests.raw


@unittest.skipUnless(importlib.util.find_spec('ortools'), 'optional OR-Tools environment')
class CpsatTests(unittest.TestCase):
    def test_dead_row_must_fit_even_when_live_count_does_not_change(self):
        data = raw([('GET', (), name) for name in 'abcdz'] + [('SET', (i,), f'out{i}') for i in range(4)])
        order, info = solve_retention_cpsat(parse_block(data), fixed_order=True)
        self.assertIsNone(order)
        self.assertEqual(info['outcome'], 'solver_proved_infeasible_stated_model')
        retention_tests.RetentionTests().check(data, schedule_retention_cpsat(parse_block(data)))

    def test_hazard_forced_dead_set_at_full_window(self):
        rows = [('GET', (), 'a') for _ in range(4)] + [('SET', (0,), 'a'), ('GET', (), 'a')]
        rows += [('ADD', (i, 5), None) for i in range(4)]
        rows += [('SET', (6 + i,), f'out{i}') for i in range(4)]
        order, info = solve_retention_cpsat(parse_block(raw(rows)))
        self.assertIsNone(order)
        self.assertEqual(info['solver_status'], 'INFEASIBLE')

    def test_full_window_refresh_constructs_and_preserves_ordered_args(self):
        data = raw([('GET', (), 'a'), ('GET', (), 'b'), ('GET', (), 'c'), ('GET', (), 'x'),
                    ('ADD', (3, 0), None), ('MULW', (4, 1), None), ('ADD', (5, 2), None),
                    ('SET', (6,), 'out'), ('SET', (0,), 'oa'), ('SET', (1,), 'ob'), ('SET', (2,), 'oc')])
        candidate = schedule_retention_cpsat(parse_block(data), fixed_order=True)
        self.assertGreater(candidate['stats']['inserted_copy_count'], 0)
        retention_tests.RetentionTests().check(data, candidate)

    def test_repeated_input_and_memory_epoch(self):
        data = raw([('GET', (), 'a'), ('ADD', (0, 0), None), ('SET', (1,), 'a'),
                    ('GET', (), 'a'), ('MULW', (0, 3), None), ('SET', (4,), 'out')])
        retention_tests.RetentionTests().check(data, schedule_retention_cpsat(parse_block(data)))

    def test_unknown_budget_and_unsupported_are_not_proofs(self):
        data = raw([('GET', (), 'a'), ('SET', (0,), 'out')])
        with self.assertRaises(BudgetExceeded): solve_retention_cpsat(parse_block(data), time_budget_ms=1e-9)
        data = {'block_id': 'copy', 'bit_width': 2, 'instructions': [
            {'op': 'GET', 'reg': 'a'}, {'op': 'COPY', 'source': 't#1'}, {'op': 'SET', 'inputs': ['t#1'], 'reg': 'out'}]}
        with self.assertRaisesRegex(InfeasibleSchedule, 'matcher failure only'):
            solve_retention_cpsat(parse_block(data))


if __name__ == '__main__': unittest.main()
