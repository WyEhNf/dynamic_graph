import unittest
from experiments.baseline_r30.isa_scheduler.incremental import schedule_incremental as reference_schedule
from isa_scheduler.incremental import schedule_incremental
from isa_scheduler.fuzz import generate
from isa_scheduler.model import InfeasibleSchedule,parse_block
from isa_scheduler.verify import verify


class FreedCountTests(unittest.TestCase):
    def test_all_priority_policies_exactly_match_frozen_dynamic_counts(self):
        policies=("stable_fast","ready_fast","pressure","demand","incremental","affinity","deadline","age_first","size_pressure")
        for seed in range(400):
            data=generate(seed,("wide","branch","highfanout","hazard")[seed%4],2+seed%4)
            block=parse_block(data)
            for policy in policies:
                try:before=reference_schedule(block,policy)
                except Exception as exc:
                    # Frozen/new model classes differ; match by exception kind.
                    self.assertEqual(type(exc).__name__,"InfeasibleSchedule")
                    with self.assertRaises(InfeasibleSchedule):schedule_incremental(block,policy)
                    continue
                after=schedule_incremental(block,policy)
                self.assertEqual(before["optimized_instructions"],after["optimized_instructions"],(seed,policy))
                self.assertEqual(before["stats"]["original_order"],after["stats"]["original_order"])
                verify(data,after)
