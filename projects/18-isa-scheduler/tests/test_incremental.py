import unittest

from isa_scheduler.fuzz import generate
from isa_scheduler.incremental import schedule_incremental
from isa_scheduler.model import InfeasibleSchedule, parse_block
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import IntegerSemantics, interpret, verify
from isa_scheduler.workloads import FAMILIES, generate_workload


class IncrementalTests(unittest.TestCase):
    def check(self, data, result):
        verify(data, result)
        regs = {r['reg']: 13 for r in data['instructions'] if r['op'] == 'GET'}
        sem = IntegerSemantics(16, True)
        self.assertEqual(interpret(data['instructions'], regs, sem),
                         interpret(result['optimized_instructions'], regs, sem))

    def test_all_topologies_and_widths(self):
        for family in FAMILIES:
            for bits in range(2, 6):
                data = generate_workload(18001, family, 128, bits)
                successes = 0
                for policy in ('pressure', 'demand', 'incremental', 'affinity'):
                    try:
                        result = schedule_incremental(parse_block(data), policy)
                    except InfeasibleSchedule:
                        continue  # Wide fronts can be truly impossible under the chosen model.
                    self.check(data, result)
                    successes += 1
                if family in ('skew_tree', 'parallel_chains'):
                    self.assertGreater(successes, 0, (family, bits))

    def test_fixed_seed_small_graphs_all_policies(self):
        for seed in range(18, 1018):
            data = generate(seed, ('wide', 'branch', 'highfanout', 'hazard')[seed % 4], 2 + seed % 4)
            for policy in ('pressure', 'demand', 'incremental', 'affinity'):
                try:
                    result = schedule_incremental(parse_block(data), policy)
                except InfeasibleSchedule:
                    continue
                self.check(data, result)

    def test_zero_copy_incumbent_proves_trivial_cost_lower_bound(self):
        data = generate_workload(18001, 'parallel_chains', 512, 2)
        result = optimize(data, time_budget_ms=1000)
        self.check(data, result)
        self.assertEqual(result['stats']['inserted_copy_count'], 0)
        self.assertEqual(result['stats']['search']['outcome'], 'optimal_under_model')

    def test_input_copy_is_preserved_and_duplicate_operands_count_once(self):
        data = {'block_id': 'copy', 'bit_width': 2, 'instructions': [
            {'id': 0, 'op': 'GET', 'reg': 'a'},
            {'id': 1, 'op': 'COPY', 'source': 't#1'},
            {'id': 2, 'op': 'ADD', 'inputs': ['t#1', 't#1']},
            {'id': 3, 'op': 'SET', 'reg': 'b', 'inputs': ['t#1']}]}
        for policy in ('pressure', 'demand', 'incremental'):
            result = schedule_incremental(parse_block(data), policy)
            self.check(data, result)
            self.assertEqual(result['stats']['total_copy_count'], 1)

    def test_fast_stable_exactly_matches_original_stable(self):
        from isa_scheduler.scheduler import schedule
        for seed in range(18, 518):
            data = generate(seed, ('wide', 'branch', 'highfanout', 'hazard')[seed % 4], 2 + seed % 4)
            block = parse_block(data)
            try:
                baseline = schedule(block, 'stable')
            except InfeasibleSchedule:
                with self.assertRaises(InfeasibleSchedule):
                    schedule_incremental(block, 'stable_fast')
                continue
            candidate = schedule_incremental(block, 'stable_fast')
            self.check(data, candidate)
            self.assertEqual(candidate['optimized_instructions'], baseline['optimized_instructions'])

    def test_fast_ready_exactly_matches_original_ready(self):
        from isa_scheduler.scheduler import schedule
        for family in FAMILIES + ('wide', 'branch', 'highfanout', 'hazard'):
            for bits in range(2, 6):
                for seed in range(18000, 18010):
                    data = generate_workload(seed, family, 128, bits) if family in FAMILIES else generate(seed, family, bits)
                    block = parse_block(data)
                    try:
                        baseline = schedule(block, 'ready')
                    except InfeasibleSchedule:
                        with self.assertRaises(InfeasibleSchedule):
                            schedule_incremental(block, 'ready_fast')
                        continue
                    candidate = schedule_incremental(block, 'ready_fast')
                    self.check(data, candidate)
                    self.assertEqual(candidate['optimized_instructions'], baseline['optimized_instructions'])

    def test_legal_original_path_retains_input_copy_and_preserves_hazards(self):
        data = {'block_id': 'original-copy', 'bit_width': 2, 'instructions': [
            {'id': 90, 'op': 'GET', 'reg': 'a'},
            {'id': 91, 'op': 'COPY', 'source': 't#1'},
            {'id': 92, 'op': 'SET', 'reg': 'a', 'inputs': ['t#1']},
            {'id': 93, 'op': 'GET', 'reg': 'a'}]}
        result = optimize(data)
        self.check(data, result)
        self.assertEqual(result['stats']['strategy'], 'original')
        self.assertEqual(result['stats']['inserted_copy_count'], 0)
        self.assertEqual(result['stats']['total_copy_count'], 1)

    def test_shared_multiple_outputs_use_verified_affinity_candidate(self):
        data = generate_workload(800001, 'multi_sink_shared', 256, 2)
        with self.assertRaises(InfeasibleSchedule):
            schedule_incremental(parse_block(data), 'pressure')
        result = optimize(data, time_budget_ms=1000)
        self.check(data, result)
        self.assertTrue(any(a['strategy'] == 'affinity' and a['status'] == 'verified' for a in result['stats']['attempts']))


if __name__ == '__main__':
    unittest.main()
