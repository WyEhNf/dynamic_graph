import unittest
from isa_scheduler.closed_subgraph import closed_subset_data
from isa_scheduler.model import parse_block
from isa_scheduler.sink_bounds import sink_spine_capacity_bound,sink_spine_projections
from isa_scheduler.spine_bounds import spine_capacity_bound
from isa_scheduler.workloads import generate_workload


class SinkBoundTests(unittest.TestCase):
    def test_projection_matches_independent_raw_json_extraction(self):
        for seed in range(980001,980021):
            data=generate_workload(seed,"cross_group_shared",256,2);block=parse_block(data)
            for terminal,indices,projected in sink_spine_projections(block):
                raw=closed_subset_data(data,indices);independent=parse_block(raw)
                self.assertEqual([(node.op,node.args,node.reg) for node in projected.instructions],
                                 [(node.op,node.args,node.reg) for node in independent.instructions])
                self.assertEqual(spine_capacity_bound(projected),spine_capacity_bound(independent))
        self.assertIsNotNone(sink_spine_capacity_bound(parse_block(generate_workload(100185,"cross_group_shared",1024,2))))

    def test_hazards_and_branching_shapes_do_not_get_false_spine_proofs(self):
        for family in ("hazard_multi","matrix_product_tile","butterfly","fanout_diamonds"):
            self.assertIsNone(sink_spine_capacity_bound(parse_block(generate_workload(1,family,128,2))))
