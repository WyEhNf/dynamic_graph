import unittest
from isa_scheduler.optimizer import optimize
from isa_scheduler.workloads import generate_workload
from isa_scheduler.verify import verify


class BoundPortfolioTests(unittest.TestCase):
    def test_explicit_early_stop_carries_valid_quality_scope(self):
        data=generate_workload(123,'near_window_spine',2048,2)
        result=optimize(data,'bound_portfolio',time_budget_ms=2000);verify(data,result)
        proof=result['stats']['approximation_certificate'];cost=result['stats']['inserted_copy_count']
        self.assertLessEqual((cost-proof['copy_lower_bound'])/cost,.005)
        self.assertEqual(result['stats']['search']['outcome'],'bounded_quality_under_spine_identity_model')
        self.assertIn('all topological orders',proof['scope'])
        self.assertFalse(any(row['strategy'] in ('beam','exact') for row in result['stats']['attempts']))

    def test_general_graph_and_zero_bound_follow_normal_portfolio(self):
        for family in ('hazard_multi','multi_sink_shared','serial_chains'):
            data=generate_workload(17,family,512,4)
            result=optimize(data,'bound_portfolio',time_budget_ms=2000);verify(data,result)
            self.assertNotIn('approximation_certificate',result['stats'])

    def test_tolerance_invalid_values_fail_closed_and_zero_requires_exact_bound(self):
        data=generate_workload(17,'near_window_spine',512,2)
        for invalid in (True,-.001,1,float('nan'),float('inf'),'0.005'):
            with self.assertRaises(ValueError):optimize(data,'bound_portfolio',bound_tolerance=invalid)
        result=optimize(data,'bound_portfolio',time_budget_ms=2000,bound_tolerance=0)
        verify(data,result)
        if 'approximation_certificate' in result['stats']:
            self.assertEqual(result['stats']['inserted_copy_count'],result['stats']['approximation_certificate']['copy_lower_bound'])
