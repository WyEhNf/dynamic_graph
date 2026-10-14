"""Source-only standalone interpretation controls, not executed at freeze."""
import copy
import unittest
from scripts.mobile_backbone_semantics import check_semantics


def complete(data):
    return {'output': {'block_id': data['block_id'], 'optimized_instructions': copy.deepcopy(data['instructions'])},
            'original_order': list(range(len(data['instructions']))), 'copies': 0}


class FlatSemanticsContracts(unittest.TestCase):
    def test_deep_4096_node_chain_without_recursive_expressions(self):
        rows = [{'id': 0, 'op': 'GET', 'reg': 'input'}]
        for node in range(1, 4095):
            rows.append({'id': node, 'op': 'ADD', 'inputs': ['t#1', 't#1']})
        rows.append({'id': 4095, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']})
        data = {'block_id': 'deep4096-symbols', 'bit_width': 2, 'instructions': rows}
        result = check_semantics(data, complete(data))
        self.assertTrue(result['independent_exact_opaque_symbols'])
        self.assertEqual(len(result['independent_integer_checks']), 6)

    def test_external_string_nonconsecutive_ids_are_only_labels(self):
        data = {'block_id': 'external-labels', 'bit_width': 2, 'instructions': [
            {'id': 'birth', 'op': 'GET', 'reg': 'a'},
            {'id': 191, 'op': 'ADD', 'inputs': ['t#1', 't#1']},
            {'id': 'output', 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]}
        candidate = complete(data)
        for index, row in enumerate(candidate['output']['optimized_instructions']):
            row['id'] = index
        self.assertTrue(check_semantics(data, candidate)['all_original_values_and_original_SET_writes_and_registers'])

    def test_ordered_ADD_operands_are_opaque_even_when_integer_commutative(self):
        data = {'block_id': 'ordered-ADD', 'bit_width': 2, 'instructions': [
            {'id': 0, 'op': 'GET', 'reg': 'a'}, {'id': 1, 'op': 'GET', 'reg': 'b'},
            {'id': 2, 'op': 'ADD', 'inputs': ['t#1', 't#2']},
            {'id': 3, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]}
        candidate = complete(data)
        candidate['output']['optimized_instructions'][2]['inputs'].reverse()
        with self.assertRaises(AssertionError):
            check_semantics(data, candidate)

    def test_SET_slots_cannot_be_REFERENCED_as_values(self):
        data = {'block_id': 'SET-slot', 'bit_width': 2, 'instructions': [
            {'id': 0, 'op': 'GET', 'reg': 'a'}, {'id': 1, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]}
        candidate = complete(data)
        candidate['output']['optimized_instructions'].append({'id': 2, 'op': 'COPY', 'source': 't#1'})
        candidate['copies'] = 1
        with self.assertRaises(ValueError):
            check_semantics(data, candidate)


if __name__ == '__main__':
    unittest.main()
