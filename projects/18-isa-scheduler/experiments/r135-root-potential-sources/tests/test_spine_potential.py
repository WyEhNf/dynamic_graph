import unittest
from unittest.mock import patch

from isa_scheduler.spine_potential import schedule_spine_potential
from isa_scheduler.model import parse_block
from isa_scheduler.workloads import generate_workload
from scripts.research_spine_age_probe import check
from tests import test_spine_macro as macro_tests


class SpinePotentialTests(unittest.TestCase):
    def test_actual_identity_cost_for_single_and_segment_actions(self):
        for family in ('cross_group_shared', 'multi_sink_irregular', 'multi_sink_shared'):
            data = generate_workload(8400001, family, 64, 3)
            for span in (1, 16):
                result = schedule_spine_potential(parse_block(data), max_span=span)
                check(data, result, result['stats']['original_order'])
                self.assertEqual(result['stats']['beam_priority'], 'potential')
                self.assertLess(len(result['stats']['selected_potential_roots']), 8)

    def test_direct_width_duplicate_hazard_and_budget_boundaries(self):
        with patch.object(macro_tests, 'schedule_spine_macro', schedule_spine_potential):
            target = macro_tests.SpineMacroTests()
            target.test_duplicate_root_direct_w2_and_w1_restriction()
            target.test_hazard_matcher_and_time_state_limits()


if __name__ == '__main__': unittest.main()
