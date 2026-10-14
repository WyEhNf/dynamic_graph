"""Prepared boundary contracts; NOT executed during the source freeze.

Synthetic dispatch sinks below are repeated *complete physical fixtures*, not
16 claimed distinct search solutions. Their purpose is wrapper dispatch only.
"""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from isa_scheduler.general_region_anytime import RegionStop, _step
from isa_scheduler.mobile_backbone_anytime import prepare_mobile, resource_layout, search_mobile_backbone
from isa_scheduler.mobile_backbone_refine import refine_mobile_backbones, select_mobile_regions
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
from scripts.raw_mobile_backbone_reference import raw_graph, solve_mobile_raw
from scripts.research_mobile_backbone_small import fanout_fixture, hazard_fixture

ROOT = Path(__file__).resolve().parents[1]


def hand():
    return json.loads((ROOT / 'research/level-stage/mobile-backbone-hand45.json').read_text(encoding='utf-8'))


class MobileContracts(unittest.TestCase):
    def test_long_span_selector_exact_mobile_and_backbone(self):
        fixture = hand()
        graph = prepare_mobile(fixture['input'], fixture['baseline'], lambda: None)
        eligible, rejected, count = select_mobile_regions(graph, fixture['baseline'], lambda: None)
        self.assertEqual(count, 1)
        self.assertEqual(eligible[0]['region'], {'L': 0, 'R': 44, 'mobile': [0, 1, 2, 43, 44]})
        self.assertEqual(rejected, [])

    def test_fixed_nonzero_physical_prefix_and_external_suffix_role(self):
        fixture = hand()
        region = {'L': 4, 'R': 8, 'mobile': [4, 5]}
        replay = MobilePhysicalReplay(fixture['input'], fixture['baseline'], region)
        self.assertEqual(replay.seed[3], 5)  # GET0,ADD1,SET2,GET3,COPY ofroot.
        self.assertEqual(replay.roles(0, 0, replay.seed[2]), ((0, 1),))
        self.assertTrue(replay.needed(0, 0, 0))  # Original MUL43 is outside region.

    def test_cursor_is_required_by_full_completed_state(self):
        fixture = hand()
        replay = MobilePhysicalReplay(fixture['input'], fixture['baseline'], {'L': 0, 'R': 44, 'mobile': [0, 1, 2, 43, 44]})
        state = replay.advance(replay.seed, 3)
        self.assertEqual(state[:2], (0, 1))
        with self.assertRaises(AssertionError):
            replay.advance(state, 3)
        with self.assertRaises(AssertionError):
            replay.advance(replay.seed, 4)

    def test_hazards_block_backbone_before_mobile_SET(self):
        data, initial = hazard_fixture()
        replay = MobilePhysicalReplay(data, initial, {'L': 0, 'R': 5, 'mobile': [0, 1, 2, 4, 5]})
        with self.assertRaises(AssertionError):
            replay.advance(replay.seed, 3)
        state = replay.seed
        for node in (0, 1, 2, 3, 4, 5):
            state = replay.advance(state, node)
        self.assertEqual(state[3], 6)
        self.assertEqual(state[2][-1], None)  # SET has no output, but consumes slot.

    def test_fanout40_root_remains_external(self):
        data, initial = fanout_fixture()
        graph = prepare_mobile(data, initial, lambda: None)
        eligible, _, _ = select_mobile_regions(graph, initial, lambda: None)
        self.assertTrue(eligible)
        self.assertNotIn(0, eligible[0]['region']['mobile'])
        self.assertEqual(len(graph['users'][0]), 40)

    def test_nonlast_operand_at_W_must_relay_before_emit(self):
        data = {'block_id': 'nonlast-W', 'bit_width': 2, 'instructions': [
            {'id': 0, 'op': 'GET', 'reg': 'x'}, {'id': 1, 'op': 'GET', 'reg': 'y'},
            {'id': 2, 'op': 'GET', 'reg': 'z'}, {'id': 3, 'op': 'GET', 'reg': 'dead'},
            {'id': 4, 'op': 'ADD', 'inputs': ['t#4', 't#3']},
            {'id': 5, 'op': 'ADD', 'inputs': ['t#5', 't#1']},
            {'id': 6, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]}
        initial_rows = [dict(row) for row in data['instructions'][:4]] + [
            {'id': 4, 'op': 'COPY', 'source': 't#4'},
            {'id': 5, 'op': 'ADD', 'inputs': ['t#1', 't#4']},
            {'id': 6, 'op': 'ADD', 'inputs': ['t#2', 't#1']},
            {'id': 7, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]
        initial = {'output': {'block_id': data['block_id'], 'optimized_instructions': initial_rows},
                   'original_order': list(range(7)), 'copies': 1}
        graph = prepare_mobile(data, initial, lambda: None)
        _, additions = _step(graph, 4, {0, 1, 2, 3}, ((0, 4), (1, 3)), lambda: None)
        self.assertEqual(additions, [{'op': 'COPY', 'source': 't#4'}, {'op': 'ADD', 'inputs': ['t#1', 't#4']}])

    def test_total_deadline_partial_keeps_initial(self):
        fixture = hand()
        result = search_mobile_backbone(fixture['input'], fixture['baseline'],
            {'L': 0, 'R': 44, 'mobile': [0, 1, 2, 43, 44]}, time_budget_ms=1e-9)
        self.assertEqual(result['stats']['outcome'], 'partial_total_deadline')
        self.assertEqual(result['best']['copies'], 13)
        self.assertEqual(result['stats']['complete_outputs'], 0)

    def test_foreign_prepared_fail_closed(self):
        fixture = hand()
        with self.assertRaises(ValueError):
            search_mobile_backbone(fixture['input'], fixture['baseline'], {'L': 0, 'R': 44, 'mobile': [0]},
                prepared={'raw_data': {}, 'incumbent': fixture['baseline']})

    def test_bad_mobile_duplicate_and_outside_interval_reject(self):
        fixture = hand()
        for region in ({'L': 0, 'R': 44, 'mobile': [0, 0]}, {'L': 4, 'R': 44, 'mobile': [0]}):
            with self.assertRaises(ValueError):
                search_mobile_backbone(fixture['input'], fixture['baseline'], region)

    def test_N_gt_9_is_not_raw_reference_proof(self):
        with self.assertRaises(ValueError):
            raw_graph(hand()['input'])

    def test_unknown_opcode_and_original_COPY_reject(self):
        data, initial = hazard_fixture()
        for op in ('SLL', 'COPY'):
            malformed = copy.deepcopy(data)
            malformed['instructions'][1] = {'id': 1, 'op': op, 'source': 't#1'}
            with self.assertRaises(ValueError):
                prepare_mobile(malformed, initial, lambda: None)
            with self.assertRaises(ValueError):
                raw_graph(malformed)

    def test_raw_reference_unknown_not_negative_proof(self):
        data, initial = hazard_fixture()
        result = solve_mobile_raw(data, initial, {'L': 0, 'R': 5, 'mobile': list(range(6))}, time_budget_ms=1e-9)
        self.assertTrue(result['outcome'].startswith('unknown'))
        self.assertIsNone(result['candidate'])

    def test_serialized_cursor_and_identifier_bounds(self):
        data, initial = hazard_fixture()
        data = copy.deepcopy(data)
        initial = copy.deepcopy(initial)
        data['instructions'][0]['reg'] = '长寄存器' * 2048
        initial['output']['optimized_instructions'][0]['reg'] = data['instructions'][0]['reg']
        layout = resource_layout(data, initial)
        self.assertLessEqual(layout['label_record_bound_bytes'], 1024)
        self.assertLessEqual(layout['open_record_bound_bytes'], 2048)
        self.assertGreater(layout['complete_proposal_bound_bytes'], 20000)

    def test_after_complete_interruption_retains_saved_output(self):
        fixture = hand()
        saved = []
        def sink(candidate):
            saved.append(candidate)
            raise RegionStop('test_after_saved_complete')
        result = search_mobile_backbone(fixture['input'], fixture['baseline'],
            {'L': 0, 'R': 44, 'mobile': [0, 1, 2, 43, 44]}, on_completed=sink)
        self.assertTrue(saved)
        self.assertEqual(result['stats']['complete_outputs'], len(saved))
        self.assertEqual(result['best']['copies'], min(13, min(item['copies'] for item in saved)))
        self.assertEqual(result['stats']['outcome'], 'partial_test_after_saved_complete')

    def test_per_region_cap_continues_next_with_same_initial(self):
        fixture = hand()
        graph = prepare_mobile(fixture['input'], fixture['baseline'], lambda: None)
        regions = [{'region': {'L': 0, 'R': 44, 'mobile': [0, 1, 2, 43, 44]}, 'anchor': 0},
                   {'region': {'L': 0, 'R': 44, 'mobile': [0, 43]}, 'anchor': 43}]
        calls, saved = [], []
        def fake_search(data, initial, region, **options):
            calls.append(initial)
            index = len(calls) - 1
            candidate = fixture['baseline'] if index == 0 else fixture['manual_mobile_witness']
            count = 16 if index == 0 else 1
            for _ in range(count):
                options['on_completed'](candidate)  # Actual callbacks, complete fixture; synthetic notdistinctsolutions.
            stats = {'processed_states': 1, 'attempted_transitions': 1, 'complete_outputs': count,
                     'outcome': 'partial_outlet_limit' if index == 0 else 'exhausted_improvement_search'}
            return {'best': candidate, 'stats': stats, 'diagnostics': 'synthetic_dispatch_only'}
        with patch('isa_scheduler.mobile_backbone_refine.prepare_mobile', return_value=graph), \
             patch('isa_scheduler.mobile_backbone_refine.select_mobile_regions', return_value=(regions, [], 2)), \
             patch('isa_scheduler.mobile_backbone_refine.search_mobile_backbone', side_effect=fake_search):
            result = refine_mobile_backbones(fixture['input'], fixture['baseline'],
                resource_snapshot=lambda: {'disk_free_bytes': 10**12}, on_completed=lambda index, candidate: saved.append(candidate))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(initial == fixture['baseline'] for initial in calls))
        self.assertEqual(result['stats']['complete_outputs'], 17)
        self.assertEqual(len(saved), 17)
        self.assertEqual(result['stats']['outlet_limited_regions'], [0])
        self.assertEqual(result['best']['copies'], 0)


if __name__ == '__main__':
    unittest.main()
