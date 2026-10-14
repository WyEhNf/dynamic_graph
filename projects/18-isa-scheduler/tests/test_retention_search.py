from dataclasses import replace
import copy
import unittest

from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.local_order import emit_order
from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule, parse_block
from isa_scheduler.retention_search import find_retention_order, schedule_retention
from isa_scheduler.retention_certificate import check_retention_certificate
from isa_scheduler.verify import IntegerSemantics, interpret, verify
from isa_scheduler.workloads import generate_workload


def raw(rows, bits=2):
    result = []
    for index, (op, args, reg) in enumerate(rows):
        row = {'id': index, 'op': op}
        if reg is not None: row['reg'] = reg
        if args: row['inputs'] = [f't#{index - source}' for source in args]
        result.append(row)
    return {'block_id': 'retention-test', 'bit_width': bits, 'instructions': result}


class RetentionTests(unittest.TestCase):
    def check(self, data, result):
        verify(data, result)
        check_identity_witness(data, result, result['stats']['original_order'])
        registers = {row['reg']: 19 - 11 * index for index, row in enumerate(data['instructions']) if row['op'] == 'GET'}
        for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
            self.assertEqual(interpret(data['instructions'], registers, semantics),
                             interpret(result['optimized_instructions'], registers, semantics))

    def test_full_window_can_rotate_to_a_last_use(self):
        data = raw([('GET', (), 'a'), ('GET', (), 'b'), ('GET', (), 'c'), ('GET', (), 'x'),
                    ('ADD', (3, 0), None), ('MULW', (4, 1), None), ('ADD', (5, 2), None),
                    ('SET', (6,), 'out'), ('SET', (0,), 'oa'), ('SET', (1,), 'ob'), ('SET', (2,), 'oc')])
        block = parse_block(data)
        # Deliberately keep three roots alive through the arithmetic chain.
        candidate = emit_order(block, list(range(len(block.instructions))), deadline=float('inf'))
        self.assertIsNotNone(candidate); self.assertGreater(candidate['stats']['inserted_copy_count'], 0)
        self.check(data, candidate)
        self.check(data, schedule_retention(block, time_budget_ms=1000))

    def test_dead_original_at_full_window_requires_reordering(self):
        data = raw([('GET', (), name) for name in 'abcdz'] +
                   [('SET', (i,), f'out{i}') for i in range(4)])
        block = parse_block(data)
        self.assertIsNone(emit_order(block, list(range(len(block.instructions))), deadline=float('inf')))
        chained = replace(block, instructions=tuple(replace(node, order_deps=(() if node.index == 0 else (node.index - 1,)))
                                                    for node in block.instructions))
        with self.assertRaisesRegex(InfeasibleSchedule, 'proven_infeasible_under_model'):
            find_retention_order(chained, time_budget_ms=1000)
        self.check(data, schedule_retention(block, time_budget_ms=1000))

    def test_memory_hazards_and_repeated_ordered_arguments(self):
        for bits in (2, 3, 4, 5):
            data = generate_workload(8270001, 'hazard_multi', 64, bits)
            self.check(data, schedule_retention(parse_block(data), time_budget_ms=1000))
        data = raw([('GET', (), 'a'), ('ADD', (0, 0), None), ('SET', (1,), 'a'),
                    ('GET', (), 'a'), ('MULW', (0, 3), None), ('SET', (4,), 'out')])
        self.check(data, schedule_retention(parse_block(data), time_budget_ms=1000))

    def test_limits_are_unknown_and_original_copy_rejected(self):
        data = generate_workload(8270101, 'cross_group_shared', 64, 3)
        with self.assertRaises(BudgetExceeded): find_retention_order(parse_block(data), max_states=1)
        data = {'block_id': 'copy', 'bit_width': 2, 'instructions': [
            {'op': 'GET', 'reg': 'a'}, {'op': 'COPY', 'source': 't#1'}, {'op': 'SET', 'inputs': ['t#1'], 'reg': 'out'}]}
        with self.assertRaisesRegex(InfeasibleSchedule, 'matcher failure only'):
            schedule_retention(parse_block(data), time_budget_ms=1000)

    def test_full_window_set_with_future_inputs_is_proven_by_raw_closure(self):
        # Four distinct original GET identities read the old epoch. WAR forces
        # all four before SET; all four are needed after a new GET. The SET's
        # dead result still occupies a physical slot and cannot last-consume.
        rows = [('GET', (), 'a') for _ in range(4)] + [('SET', (0,), 'a'), ('GET', (), 'a')]
        rows += [('ADD', (index, 5), None) for index in range(4)]
        rows += [('SET', (6 + index,), f'out{index}') for index in range(4)]
        data = raw(rows)
        with self.assertRaises(InfeasibleSchedule) as caught:
            find_retention_order(parse_block(data), time_budget_ms=1000)
        certificate = caught.exception.retention_certificate
        self.assertTrue(check_retention_certificate(data, certificate)['verified_infeasible_under_original_identity_model'])
        changed = copy.deepcopy(certificate); changed['completed_masks_hex'].remove('0x0')
        with self.assertRaises(ValueError): check_retention_certificate(data, changed)
        changed = copy.deepcopy(certificate); changed['original_order_dependencies'][4] = []
        with self.assertRaises(ValueError): check_retention_certificate(data, changed)
        changed = copy.deepcopy(certificate); changed['completed_masks_hex'] = ['0x0']
        with self.assertRaises(ValueError): check_retention_certificate(data, changed)


if __name__ == '__main__': unittest.main()
