import unittest
from unittest.mock import patch

from isa_scheduler.spine_lifetime import schedule_spine_lifetime
from isa_scheduler.model import parse_block, InfeasibleSchedule
from isa_scheduler.workloads import generate_workload
from scripts.research_spine_age_probe import check
from scripts.research_lifetime_state_audit import audit, generated
from tests import test_spine_macro as macro_tests


class SpineLifetimeTests(unittest.TestCase):
    def test_actual_identity_cost_single_and_macro(self):
        for family in ('cross_group_shared', 'multi_sink_irregular', 'multi_sink_shared'):
            data = generate_workload(8430001, family, 64, 3)
            for span in (1, 16):
                result = schedule_spine_lifetime(parse_block(data), max_span=span)
                check(data, result, result['stats']['original_order'])
                self.assertEqual(result['stats']['beam_priority'], 'lifetime')

    def test_duplicate_width_hazard_budget_and_empty_branch_rejected(self):
        with patch.object(macro_tests, 'schedule_spine_macro', schedule_spine_lifetime):
            target = macro_tests.SpineMacroTests()
            target.test_duplicate_root_direct_w2_and_w1_restriction()
            target.test_hazard_matcher_and_time_state_limits()
        data = {'block_id': 'direct-sink', 'bit_width': 2,
                'instructions': [{'id': 0, 'op': 'GET', 'reg': 'a'},
                                 {'id': 1, 'op': 'SET', 'inputs': ['t#1'], 'reg': 'out'}]}
        with self.assertRaisesRegex(InfeasibleSchedule, 'empty arithmetic branch unsupported.*matcher|branch_copy.*no global proof'):
            schedule_spine_lifetime(parse_block(data))

    def test_all_state_oracle_unknown_controls(self):
        data = generated(8440001, 'fork')
        for kwargs in ({'max_states': 1}, {'budget_ms': 1e-9}):
            result = audit(data, **kwargs)
            self.assertEqual(result['status'], 'unknown_enumeration_budget')
            self.assertNotIn('finite_remaining_states', result)
            self.assertNotIn('violations', result)


if __name__ == '__main__': unittest.main()
