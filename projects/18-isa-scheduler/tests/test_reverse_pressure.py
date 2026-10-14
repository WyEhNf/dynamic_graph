import unittest
from time import perf_counter
from isa_scheduler.model import parse_block,BudgetExceeded,InfeasibleSchedule
from isa_scheduler.reverse_pressure import propose_order,schedule_reverse_pressure
from isa_scheduler.workloads import FAMILIES,generate_workload
from isa_scheduler.verify import verify,IntegerSemantics,interpret
from isa_scheduler.identity_witness import check_identity_witness

class ReversePressureTests(unittest.TestCase):
 def test_topological_permutation_and_independent_outputs(self):
  # Fresh holdout families/windows; fixed-order failures are NOT proof failures.
  successes=0
  for policy in ('reverse_pressure','reverse_cluster','reverse_span','consumer_cluster'):
   for k,family in enumerate(FAMILIES):
    for bits in (2,3,4,5):
     data=generate_workload(6100001+k*4+bits,family,32,bits);block=parse_block(data)
     order,_=propose_order(block,policy=policy);self.assertEqual(sorted(order),list(range(len(order))))
     positions={value:i for i,value in enumerate(order)}
     for node in block.instructions:
      self.assertTrue(all(positions[s]<positions[node.index]for s in (*node.args,*node.order_deps)))
     try:output=schedule_reverse_pressure(block,policy=policy,time_budget_ms=200)
     except InfeasibleSchedule:continue
     verify(data,output);check_identity_witness(data,output,output['stats']['original_order']);successes+=1
     inputs={node['reg']:-7+11*i for i,node in enumerate(data['instructions'])if node['op']=='GET'}
     for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
      self.assertEqual(interpret(data['instructions'],inputs,semantics),interpret(output['optimized_instructions'],inputs,semantics))
  self.assertGreater(successes,100)
 def test_budget_and_policy_reject(self):
  block=parse_block(generate_workload(6100301,'wide_fanout',32,2))
  with self.assertRaises(BudgetExceeded):propose_order(block,deadline=perf_counter()-1)
  with self.assertRaises(ValueError):propose_order(block,policy='unknown')
