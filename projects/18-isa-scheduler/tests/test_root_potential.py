import copy
import unittest

from isa_scheduler.model import InvalidBlock
from isa_scheduler.root_potential_bound import propose_root_potential_bound, check_root_potential_bound
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify
from tests.test_retention_search import raw
from scripts.research_retention_audit import raw_physical_oracle


class RootPotentialTests(unittest.TestCase):
    def test_positive_chain_and_all_window_boundaries(self):
        rows = [('GET', (), 'a'), ('GET', (), 'private')]
        previous = 1
        for offset in range(10):
            rows.append(('ADD', (previous, 0), None)); previous = len(rows) - 1
        rows.append(('SET', (previous,), 'out')); rows.append(('GET', (), 'unused'))
        for bits in (2, 3, 4, 5):
            data = raw(rows, bits); certificate = propose_root_potential_bound(data)
            lower = check_root_potential_bound(data, certificate)['lower_bound']
            exact = raw_physical_oracle(data, time_budget_ms=2000)
            self.assertEqual(exact['status'], 'feasible_optimal_copy')
            self.assertLessEqual(lower, exact['copies'])
            if bits == 2: self.assertGreater(lower, 0)

    def test_nonlatest_copy_remains_identity_and_semantically_valid(self):
        data = raw([('GET', (), 'a'), ('GET', (), 'b'), ('ADD', (0, 1), None), ('SET', (2,), 'out')])
        output = {'block_id': data['block_id'], 'optimized_instructions': [
            {'id': 0, 'op': 'GET', 'reg': 'a'}, {'id': 1, 'op': 'GET', 'reg': 'b'},
            {'id': 2, 'op': 'COPY', 'source': 't#2'},
            {'id': 3, 'op': 'COPY', 'source': 't#3'},
            {'id': 4, 'op': 'ADD', 'inputs': ['t#1', 't#3']},
            {'id': 5, 'op': 'SET', 'inputs': ['t#1'], 'reg': 'out'}]}
        verify(data, output); check_identity_witness(data, output, [0, 1, 2, 3])
        # Before second COPY latest a is age1, actual older source age3.
        self.assertEqual((2 - 1) / (4 - 2), .5)
        self.assertNotEqual((2 - 1) / (4 - 2), (2 - 3) / (4 - 2))

    def test_fraction_certificate_tamper_and_unsupported(self):
        data = raw([('GET', (), 'a'), ('GET', (), 'p'), ('ADD', (0, 1), None),
                    ('ADD', (2, 0), None), ('SET', (3,), 'out'), ('GET', (), 'unused')])
        cert = propose_root_potential_bound(data)
        for field, value in [('lower_bound', 999), ('selected_roots', [5]),
                             ('selected_roots', [0, 0]), ('window', 32),
                             ('gain_fraction', [1000, 1]), ('mandatory_histogram', [1000, 0])]:
            broken = copy.deepcopy(cert); broken[field] = value
            with self.assertRaises(InvalidBlock): check_root_potential_bound(data, broken)
        broken = copy.deepcopy(data); broken['instructions'][2]['op'] = 'COPY'
        broken['instructions'][2].pop('inputs'); broken['instructions'][2]['source'] = 't#1'
        with self.assertRaises(InvalidBlock): propose_root_potential_bound(broken)


if __name__ == '__main__': unittest.main()
