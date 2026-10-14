from dataclasses import replace
import unittest

from isa_scheduler.model import parse_block, InfeasibleSchedule, BudgetExceeded
from isa_scheduler.spine_age import schedule_spine_age
from isa_scheduler.incremental import PreparedGraph
from isa_scheduler.workloads import generate_workload
from tests import test_retention_search as retention_tests


class SpineAgeTests(unittest.TestCase):
    def test_shared_original_prefixes_and_true_physical_cost(self):
        for family in ('cross_group_shared', 'multi_sink_irregular', 'multi_sink_shared'):
            data = generate_workload(8360001, family, 64, 4)
            candidate = schedule_spine_age(parse_block(data), time_budget_ms=2000, beam_width=4)
            retention_tests.RetentionTests().check(data, candidate)

    def test_ordered_args_and_duplicate_carry(self):
        rows = [('GET', (), 'a'), ('GET', (), 'p'), ('ADD', (1, 0), None),
                ('MULW', (2, 2), None), ('ADD', (0, 3), None), ('SET', (4,), 'out'),
                ('GET', (), 'q'), ('MULW', (0, 6), None), ('ADD', (7, 7), None), ('SET', (8,), 'out2')]
        data = retention_tests.raw(rows, 3)
        retention_tests.RetentionTests().check(data, schedule_spine_age(parse_block(data), beam_width=4))

    def test_unmatched_hazard_and_budget_not_infeasible_proofs(self):
        data = generate_workload(8360002, 'hazard_multi', 64, 3)
        with self.assertRaises(InfeasibleSchedule) as caught: schedule_spine_age(parse_block(data))
        self.assertNotIn('proven_infeasible', str(caught.exception))
        data = generate_workload(8360003, 'cross_group_shared', 64, 3)
        with self.assertRaises(BudgetExceeded): schedule_spine_age(parse_block(data), max_states=1)

    def test_direct_w1_is_explicitly_unsupported_even_for_feasible_chain(self):
        for rows in (
            [('GET', (), 'a'), ('MULW', (0, 0), None), ('SET', (1,), 'out')],
            [('GET', (), 'a'), ('MULW', (0, 0), None), ('SET', (1,), 'out'),
             ('ADD', (0, 0), None), ('SET', (3,), 'out2')],
        ):
            block = replace(parse_block(retention_tests.raw(rows)), bit_width=0)
            with self.assertRaisesRegex(InfeasibleSchedule, 'W1 unsupported.*matcher restriction only'):
                schedule_spine_age(block)

    def test_direct_w2_shared_roots_and_unused_get(self):
        rows = [('GET', (), 'unused'), ('GET', (), 'a'), ('MULW', (1, 1), None),
                ('SET', (2,), 'out'), ('ADD', (1, 1), None), ('SET', (4,), 'out2')]
        data = retention_tests.raw(rows)
        block = replace(parse_block(data), bit_width=1)
        output = schedule_spine_age(block, beam_width=4)
        retention_tests.RetentionTests().check(data, output)
        for row in output['optimized_instructions']:
            for token in row.get('inputs', []) + ([row['source']] if 'source' in row else []):
                self.assertLessEqual(int(token[2:]), 2)

    def test_prepared_block_identity_and_preprocessing_budget(self):
        data = generate_workload(8360004, 'cross_group_shared', 64, 3)
        block = parse_block(data)
        with self.assertRaisesRegex(ValueError, 'another block'):
            schedule_spine_age(block, prepared=PreparedGraph(parse_block(data)))
        with self.assertRaises(BudgetExceeded): schedule_spine_age(block, time_budget_ms=1e-9)


if __name__ == '__main__': unittest.main()
