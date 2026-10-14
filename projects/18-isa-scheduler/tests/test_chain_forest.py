import unittest
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload
from unittest.mock import patch


class ChainForestTests(unittest.TestCase):
    def test_direct_zero_copy_without_general_preparation(self):
        for seed in range(100):
            data=generate_workload(seed,"serial_chains",128,2+seed%4)
            with patch("isa_scheduler.optimizer.PreparedGraph",side_effect=AssertionError("General preprocessing used")):
                result=optimize(data,time_budget_ms=1000)
            verify(data,result)
            self.assertEqual(result["stats"]["inserted_copy_count"],0)
            self.assertEqual(sorted(result["stats"]["original_order"]),list(range(len(data["instructions"]))))

    def test_conservative_memory_hazards_not_screened_in(self):
        data=generate_workload(30,"serial_chains",64,3)
        with patch("isa_scheduler.optimizer.emit_single_source_chains",side_effect=AssertionError("Unsafe direct path")):
            result=optimize(data,time_budget_ms=1000,memory_order="conservative")
        verify(data,result)
