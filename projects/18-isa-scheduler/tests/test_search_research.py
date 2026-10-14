import unittest
from isa_scheduler.fuzz import generate
from isa_scheduler.model import InfeasibleSchedule, parse_block
from isa_scheduler.search import search
from isa_scheduler.verify import verify


class SearchResearchTests(unittest.TestCase):
    def test_cost_order_and_age_dominance_match_exhaustive_reference(self):
        for seed in range(18000, 18200):
            data = generate(seed, ('wide', 'branch', 'highfanout', 'hazard')[seed % 4], 2 + seed % 4)
            block = parse_block(data)
            try:
                baseline = search(block, dominance=False, progress_tie=False, time_budget_ms=1000)
            except InfeasibleSchedule:
                with self.assertRaises(InfeasibleSchedule):
                    search(block, time_budget_ms=1000)
                continue
            current = search(block, time_budget_ms=1000, dominance=True)
            verify(data, current)
            self.assertEqual(current['stats']['inserted_copy_count'], baseline['stats']['inserted_copy_count'])
            self.assertEqual(current['stats']['search']['outcome'], 'optimal_under_model')

    def test_beam_does_not_apply_global_age_dominance(self):
        data = generate(19, 'branch', 2)
        result = search(parse_block(data), beam_width=128, time_budget_ms=1000)
        verify(data, result)
        self.assertFalse(result['stats']['search']['dominance_enabled'])
        self.assertNotEqual(result['stats']['search']['outcome'], 'optimal_under_model')


if __name__ == '__main__':
    unittest.main()
