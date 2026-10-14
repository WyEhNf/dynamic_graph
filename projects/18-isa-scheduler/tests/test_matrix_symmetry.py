import copy
import importlib.util
import unittest

from isa_scheduler.matrix_symmetry import propose_matrix_symmetry, check_matrix_symmetry
from isa_scheduler.model import parse_block, InfeasibleSchedule
from isa_scheduler.retention_search import find_retention_order
from isa_scheduler.retention_certificate import check_retention_certificate
from isa_scheduler.workloads import generate_workload
from isa_scheduler.retention_cpsat import solve_retention_cpsat
from isa_scheduler.local_order import emit_order
from tests import test_retention_search as retention_tests


class SymmetryTests(unittest.TestCase):
    def test_raw_automorphism_all_orig_nodes_and_tampering(self):
        for size in (32, 256, 1024):
            data = generate_workload(8340001, 'matrix_product_tile', size, 5)
            plan = propose_matrix_symmetry(parse_block(data))
            self.assertIsNotNone(plan)
            check_matrix_symmetry(data, plan)
            changed = copy.deepcopy(plan); changed['row_generators'][0][0] = changed['row_generators'][0][1]
            with self.assertRaises(ValueError): check_matrix_symmetry(data, changed)
            changed = copy.deepcopy(plan); changed['row_groups'][0][0] = changed['column_groups'][0][0]
            with self.assertRaises(ValueError): check_matrix_symmetry(data, changed)

    def test_names_and_ordered_arithmetic_args_are_not_assumed(self):
        data = generate_workload(8340002, 'matrix_product_tile', 256, 4)
        for index, row in enumerate(data['instructions']):
            row['id'] = f'opaque-{index * 13}'
            if 'reg' in row: row['reg'] = f'opaque-register-{index}'
            if row['op'] in ('ADD', 'MULW'): row['inputs'].reverse()
        plan = propose_matrix_symmetry(parse_block(data)); self.assertIsNotNone(plan)
        check_matrix_symmetry(data, plan)

    def test_hazard_and_false_structure_reject(self):
        data = generate_workload(8340003, 'matrix_product_tile', 32, 3)
        original = copy.deepcopy(data); plan = propose_matrix_symmetry(parse_block(data))
        reads = [row for row in data['instructions'] if row['op'] == 'GET']
        reads[1]['reg'] = reads[0]['reg']
        self.assertIsNone(propose_matrix_symmetry(parse_block(data)))
        with self.assertRaises(ValueError): check_matrix_symmetry(data, plan)
        arithmetic = next(row for row in original['instructions'] if row['op'] == 'ADD')
        arithmetic['op'] = 'MULW'
        self.assertIsNone(propose_matrix_symmetry(parse_block(original)))

    @unittest.skipUnless(importlib.util.find_spec('ortools'), 'optional OR-Tools environment')
    def test_small_plain_and_sorted_models_include_negative_and_positive(self):
        for bits in (2, 3, 4, 5):
            data = generate_workload(8340004, 'matrix_product_tile', 32, bits)
            block = parse_block(data); plan = propose_matrix_symmetry(block)
            for symmetry in (None, plan):
                order, info = solve_retention_cpsat(block, time_budget_ms=2000, symmetry_plan=symmetry)
                if bits == 2:
                    self.assertIsNone(order)
                    self.assertEqual(info['solver_status'], 'INFEASIBLE')
                    with self.assertRaises(InfeasibleSchedule) as caught:
                        find_retention_order(block, time_budget_ms=2000, max_states=100000)
                    check_retention_certificate(data, caught.exception.retention_certificate)
                    continue
                self.assertIsNotNone(order, info)
                output = emit_order(block, order, deadline=float('inf'))
                retention_tests.RetentionTests().check(data, output)
                if symmetry:
                    positions = {original: offset for offset, original in enumerate(order)}
                    for axis in ('row_groups', 'column_groups'):
                        births = [min(positions[root] for root in group) for group in plan[axis]]
                        self.assertEqual(births, sorted(births))


if __name__ == '__main__': unittest.main()
