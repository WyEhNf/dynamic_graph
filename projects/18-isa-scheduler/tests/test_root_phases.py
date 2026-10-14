import unittest
from isa_scheduler.root_phases import schedule_root_phases
from isa_scheduler.model import parse_block,InfeasibleSchedule
from isa_scheduler.workloads import generate_workload
from isa_scheduler.verify import verify,IntegerSemantics,interpret
from isa_scheduler.identity_witness import check_identity_witness

class RootPhaseTests(unittest.TestCase):
 def test_holdout_four_windows_and_independent_identity_semantics(self):
  successes=0
  for family in('cross_group_shared','multi_sink_irregular','multi_sink_shared','wide_fanout'):
   for bits in(2,3,4,5):
    data=generate_workload(7920001+bits,family,128,bits)
    try:result=schedule_root_phases(parse_block(data),time_budget_ms=1000)
    except InfeasibleSchedule:continue
    verify(data,result);check_identity_witness(data,result,result['stats']['original_order']);successes+=1
    initial={r['reg']:17-7*i for i,r in enumerate(data['instructions'])if r['op']=='GET'}
    for semantics in(IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
     self.assertEqual(interpret(data['instructions'],initial,semantics),interpret(result['optimized_instructions'],initial,semantics))
  self.assertGreaterEqual(successes,10)
 def test_hazards_and_shared_arithmetic_fail_closed(self):
  for family in('hazard_multi','dot_product_many','butterfly'):
   with self.assertRaises(InfeasibleSchedule):schedule_root_phases(parse_block(generate_workload(7920101,family,128,4)),time_budget_ms=1000)
