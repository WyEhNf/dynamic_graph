import itertools
from pathlib import Path
import random
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prefix_memory_certificates import analyze_prefix


class PrefixMemoryTests(unittest.TestCase):
    def test_bounds_against_all_serial_extensions_of_small_graphs(self):
        rng = random.Random(271012)
        compared = 0
        for trial in range(24):
            nodes = [{'id': i, 'inputs': [j for j in range(i) if rng.random() < .25],
                      'workspace_memory': rng.randrange(6), 'output_memory': rng.randrange(8)} for i in range(5)]
            successors = {i: [n['id'] for n in nodes if i in n['inputs']] for i in range(5)}
            for order in itertools.permutations(range(5)):
                positions = {key: i for i, key in enumerate(order)}
                if any(positions[p] >= positions[n['id']] for n in nodes for p in n['inputs']): continue
                actual_BEGIN = {}
                done = set()
                for key in order:
                    live = sum(nodes[p]['output_memory'] for p in done if not successors[p] or any(c not in done for c in successors[p]))
                    actual_BEGIN[key] = live + nodes[key]['workspace_memory'] + nodes[key]['output_memory']
                    done.add(key)
                for length in range(5):
                    report = analyze_prefix(nodes, order[:length], 0)
                    for certificate in report['certificates']:
                        self.assertLessEqual(certificate['necessary_BEGIN_bound'], actual_BEGIN[certificate['target_id']])
                        compared += 1
        self.assertGreater(compared, 1000)

    def test_sink_retention_completed_targets_and_bigints(self):
        huge = 2**63 - 1
        nodes = [{'id': 'sink', 'inputs': [], 'workspace_memory': 0, 'output_memory': huge},
                 {'id': 8, 'inputs': [], 'workspace_memory': 1, 'output_memory': huge}]
        report = analyze_prefix(nodes, ['sink'], huge)
        self.assertEqual(report['certificates'][0]['necessary_BEGIN_bound'], 2 * huge + 1)
        self.assertEqual(report['certificates'][0]['earliest_obstructed_prefix']['prefix_length'], 0)
        self.assertNotIn('sink', report['checked_target_ids'])

    def test_prefix_crossing_and_unknown_budget(self):
        nodes = [{'id': 0, 'inputs': [], 'workspace_memory': 0, 'output_memory': 4},
                 {'id': 1, 'inputs': [], 'workspace_memory': 3, 'output_memory': 4}]
        certificate = analyze_prefix(nodes, [0], 8)['certificates'][0]
        self.assertEqual(certificate['earliest_obstructed_prefix'], {'prefix_length': 1, 'producer_id': 0})
        self.assertEqual(certificate['irreducible_extra_cover_ids'], [0])
        report = analyze_prefix(nodes, [], 8, work_limit=1)
        self.assertEqual(report['status'], 'PARTIAL_WORK_BUDGET_UNKNOWN_TARGETS')
        self.assertEqual(report['unchecked_target_ids'], [0, 1])

    def test_bad_graph_or_non_topological_prefix_rejected(self):
        nodes = [{'id': 0, 'inputs': [], 'workspace_memory': 0, 'output_memory': 1},
                 {'id': 1, 'inputs': [0], 'workspace_memory': 0, 'output_memory': 1}]
        for prefix in ([1], [0, 0], [99]):
            with self.assertRaises(ValueError): analyze_prefix(nodes, prefix, 8)
        nodes[0]['inputs'] = [1]
        with self.assertRaises(ValueError): analyze_prefix(nodes, [], 8)
