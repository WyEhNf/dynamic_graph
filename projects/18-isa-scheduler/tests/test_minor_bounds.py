import copy,unittest
from isa_scheduler.minor_bounds import contraction_bound,check_contraction_certificate
from isa_scheduler.model import parse_block,BudgetExceeded,InvalidBlock
from isa_scheduler.fuzz import generate
from isa_scheduler.relaxed_capacity import capacity_oracle
from isa_scheduler.workloads import generate_workload


class MinorBoundTests(unittest.TestCase):
    def test_200_small_graphs_against_complete_capacity_oracle(self):
        for seed in range(200):
            data=generate(seed,('wide','branch','highfanout','hazard')[seed%4],2+seed%4)
            certificate=contraction_bound(data,time_budget_ms=1000)
            checked=check_contraction_certificate(data,certificate)
            oracle=capacity_oracle(parse_block(data),max_nodes=20,time_budget_ms=1000)
            if checked['infeasible_under_identity_model']:
                self.assertEqual(oracle['outcome'],'proven_infeasible_relaxed_capacity_under_model')

    def test_current_matrix_minor_and_tampered_evidence(self):
        data=generate_workload(3400001,'matrix_product_tile',256,2)
        certificate=contraction_bound(data,time_budget_ms=1000)
        self.assertTrue(check_contraction_certificate(data,certificate)['infeasible_under_identity_model'])
        for key,value in (('input_sha256','wrong'),('window',32),('lower_bound',100000)):
            bad={**certificate,key:value}
            with self.assertRaises(InvalidBlock):check_contraction_certificate(data,bad)
        bad=copy.deepcopy(certificate);bad['actions']=[['contract',0,0]]
        with self.assertRaises(InvalidBlock):check_contraction_certificate(data,bad)

    def test_budget_lower_bound_is_never_claimed_exact_or_infeasible(self):
        data=generate_workload(9,'matrix_product_tile',4096,5)
        result=contraction_bound(data,time_budget_ms=.000001)
        self.assertFalse(check_contraction_certificate(data,result)['infeasible_under_identity_model'])
        self.assertEqual(result['outcome'],'time_budget_exhausted_lower_bound_only')
        self.assertIsNone(contraction_bound(data,max_nodes=1))
