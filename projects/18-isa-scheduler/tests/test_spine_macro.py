from dataclasses import replace
import unittest

from isa_scheduler.incremental import PreparedGraph
from isa_scheduler.model import parse_block, BudgetExceeded, InfeasibleSchedule
from isa_scheduler.spine_macro import schedule_spine_macro
from tests import test_retention_search as retention_tests


class SpineMacroTests(unittest.TestCase):
    def test_crossing_runs_ordered_args_last_uses_unused(self):
        rows = [('GET', (), 'unused'), ('GET', (), 'a'), ('GET', (), 'b'), ('GET', (), 'x')]
        for branch in range(3):
            private = len(rows); rows.append(('GET', (), f'p{branch}'))
            previous = private
            for offset, root in enumerate(([1] * 5 + [2] * 3 + [1] * 2 + [3],
                                           [2] * 4 + [1] * 3 + [3] * 2,
                                           [3] * 4 + [1] * 2 + [2] * 4)[branch]):
                args = (previous, root) if offset % 2 else (root, previous)
                rows.append(('ADD' if offset % 3 else 'MULW', args, None))
                previous = len(rows) - 1
            rows.append(('SET', (previous,), f'out{branch}'))
        for bits in (3, 4, 5):
            data = retention_tests.raw(rows, bits)
            candidate = schedule_spine_macro(parse_block(data), time_budget_ms=2000,
                                            beam_width=4, max_span=8)
            retention_tests.RetentionTests().check(data, candidate)
            self.assertGreater(candidate['stats']['macro_actions'], 0)
            self.assertEqual(len(candidate['stats']['original_order']), len(rows))
        # W4 narrow beams may prematurely start branches. This is a matcher
        # search failure, not a negative certificate; don't hide the boundary.
        with self.assertRaisesRegex(InfeasibleSchedule, 'restricted beam.*no infeasibility proof'):
            schedule_spine_macro(parse_block(retention_tests.raw(rows, 2)), beam_width=4)

    def test_duplicate_root_direct_w2_and_w1_restriction(self):
        data = retention_tests.raw([('GET', (), 'unused'), ('GET', (), 'a'),
                                   ('MULW', (1, 1), None), ('ADD', (2, 1), None),
                                   ('MULW', (1, 3), None), ('SET', (4,), 'out')])
        block = replace(parse_block(data), bit_width=1)
        candidate = schedule_spine_macro(block)
        retention_tests.RetentionTests().check(data, candidate)
        for row in candidate['optimized_instructions']:
            for token in row.get('inputs', []) + ([row['source']] if 'source' in row else []):
                self.assertLessEqual(int(token[2:]), 2)
        with self.assertRaisesRegex(InfeasibleSchedule, 'W1 unsupported.*matcher'):
            schedule_spine_macro(replace(block, bit_width=0))

    def test_hazard_matcher_and_time_state_limits(self):
        data = retention_tests.raw([('GET', (), 'a'), ('ADD', (0, 0), None),
                                   ('SET', (1,), 'a'), ('GET', (), 'a'),
                                   ('ADD', (3, 3), None), ('SET', (4,), 'out')])
        with self.assertRaises(InfeasibleSchedule): schedule_spine_macro(parse_block(data))
        data = retention_tests.raw([('GET', (), 'a'), ('ADD', (0, 0), None),
                                   ('ADD', (1, 0), None), ('SET', (2,), 'out')])
        block = parse_block(data)
        with self.assertRaises(BudgetExceeded): schedule_spine_macro(block, max_states=1)
        with self.assertRaises(BudgetExceeded): schedule_spine_macro(block, time_budget_ms=1e-9)
        with self.assertRaisesRegex(ValueError, 'another block'):
            schedule_spine_macro(block, prepared=PreparedGraph(parse_block(data)))


if __name__ == '__main__': unittest.main()
