import copy
import unittest

from isa_scheduler.model import parse_block
from isa_scheduler.rook_minor import propose_rook_minor, check_rook_minor
from isa_scheduler.workloads import generate_workload


class RookMinorTests(unittest.TestCase):
    def test_actual_graphs_formula_and_strict_window_boundary(self):
        for target, dimension, lower in ((24, 2, 2), (72, 3, 5), (160, 4, 9), (784, 7, 27), (3744, 12, 77)):
            for bits in (2, 3, 4, 5):
                data = generate_workload(8310001, 'matrix_product_tile', target, bits)
                certificate = propose_rook_minor(parse_block(data), time_budget_ms=1000)
                self.assertIsNotNone(certificate)
                proof = check_rook_minor(data, certificate)
                self.assertEqual(proof['verified_rook_dimension'], dimension)
                self.assertEqual(proof['verified_treewidth_lower_bound'], lower)
                self.assertEqual(proof['verified_required_edges'], dimension ** 2 * (dimension - 1))
                self.assertEqual(proof['verified_infeasible_under_original_identity_model'], lower > 2 ** bits)

    def test_does_not_depend_on_family_names_or_commutative_operand_labels(self):
        data = generate_workload(8310002, 'matrix_product_tile', 72, 2)
        data['block_id'] = 'opaque-private-cores'
        for index, row in enumerate(data['instructions']):
            row['id'] = f'opaque-{index}'
            if 'reg' in row: row['reg'] = f'opaque-register-{index}'
            if len(row.get('inputs', [])) == 2: row['inputs'].reverse()
            if row['op'] == 'MULW' and index % 2: row['op'] = 'ADD'
        proof = check_rook_minor(data, propose_rook_minor(parse_block(data)))
        self.assertTrue(proof['verified_infeasible_under_original_identity_model'])

    def test_overlap_disconnection_missing_edges_and_bound_tampering_rejected(self):
        data = generate_workload(8310003, 'matrix_product_tile', 72, 2)
        certificate = propose_rook_minor(parse_block(data))
        changed = copy.deepcopy(certificate); changed['branch_sets'][1].append(changed['branch_sets'][0][0])
        with self.assertRaises(ValueError): check_rook_minor(data, changed)
        changed = copy.deepcopy(certificate)
        changed['branch_sets'][0] = [index for index in changed['branch_sets'][0] if data['instructions'][index]['op'] == 'GET']
        with self.assertRaisesRegex(ValueError, 'connected'): check_rook_minor(data, changed)
        changed = copy.deepcopy(certificate)
        for members in changed['branch_sets']:
            members[:] = [index for index in members if not data['instructions'][index].get('reg', '').startswith('a')]
        with self.assertRaises(ValueError): check_rook_minor(data, changed)
        changed = copy.deepcopy(certificate); changed['treewidth_lower_bound'] += 1
        with self.assertRaises(ValueError): check_rook_minor(data, changed)

    def test_unmatched_graph_is_not_proof(self):
        for family in ('cross_group_shared', 'dot_product_many', 'hazard_multi', 'sparse_shared'):
            data = generate_workload(8310004, family, 128, 3)
            self.assertIsNone(propose_rook_minor(parse_block(data)))


if __name__ == '__main__': unittest.main()
