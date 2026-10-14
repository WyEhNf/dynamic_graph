import unittest

from isa_scheduler.model import parse_block, BudgetExceeded
from isa_scheduler.tree_pipeline import schedule_tree_pipeline
from scripts.research_tree_pipeline_gold import generated
from scripts.research_spine_age_probe import check
from scripts.research_tree_age_audit import generated as tree_case


class TreePipelineTests(unittest.TestCase):
    def test_complete10_originals_zero_copy(self):
        data, _ = generated(4, 4, 2)
        result = schedule_tree_pipeline(parse_block(data))
        check(data, result, result['stats']['original_order'])
        self.assertEqual(result['stats']['inserted_copy_count'], 0)
        self.assertEqual(len(result['stats']['original_order']), 10)
        self.assertGreater(result['stats']['tree_age']['pair_contexts'], 0)

    def test_nested_external_roles_and_unused_gets(self):
        for seed in (8440057, 8440073, 8440101):
            data = tree_case(seed, 2, 'padded' if seed != 8440101 else 'ragged')
            result = schedule_tree_pipeline(parse_block(data), max_outcomes=1024)
            check(data, result, result['stats']['original_order'])
            self.assertEqual(len(result['stats']['original_order']), len(data['instructions']))

    def test_state_and_total_time_budget_unknown(self):
        data, _ = generated(4, 4, 2)
        with self.assertRaises(BudgetExceeded): schedule_tree_pipeline(parse_block(data), max_states=1)
        with self.assertRaises(BudgetExceeded): schedule_tree_pipeline(parse_block(data), time_budget_ms=1e-9)


if __name__ == '__main__': unittest.main()
