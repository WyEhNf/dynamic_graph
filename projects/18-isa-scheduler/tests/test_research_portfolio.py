import unittest
from isa_scheduler.optimizer import optimize
from isa_scheduler.workloads import generate_workload
from isa_scheduler.verify import verify,IntegerSemantics,interpret
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.model import InfeasibleSchedule

class ResearchPortfolioTests(unittest.TestCase):
 def test_structural_candidates_and_old_fallbacks(self):
  for family in ('padded_tree','ragged_tree','balanced_tree','unbalanced_root_stars','multi_sink_shared','ladder_diamond','hazard_multi'):
   for bits in (2,3,4,5):
    data=generate_workload(6700001+bits,family,128,bits)
    try:result=optimize(data,'research_portfolio',time_budget_ms=500)
    except InfeasibleSchedule as exc:
     self.assertIn('proven_infeasible_under_model',str(exc));continue
    verify(data,result);check_identity_witness(data,result,result['stats']['original_order'])
    inputs={r['reg']:5+i for i,r in enumerate(data['instructions'])if r['op']=='GET'}
    for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
     self.assertEqual(interpret(data['instructions'],inputs,semantics),interpret(result['optimized_instructions'],inputs,semantics))
