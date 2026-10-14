import unittest
from isa_scheduler.model import parse_block
from isa_scheduler.comb_forest import recognize_comb_forest,schedule_comb_forest
from isa_scheduler.workloads import generate_workload
from isa_scheduler.verify import verify,IntegerSemantics,interpret
from isa_scheduler.identity_witness import check_identity_witness

class CombForestTests(unittest.TestCase):
 def test_four_windows_zero_copy_and_original_identity(self):
  for family in ('skew_tree','serial_chains','parallel_chains'):
   for bits in (2,3,4,5):
    for size in (8,64,512,8192):
     data=generate_workload(7000001+size+bits,family,size,bits)
     result=schedule_comb_forest(parse_block(data),time_budget_ms=2000)
     self.assertEqual(result['stats']['inserted_copy_count'],0)
     verify(data,result);check_identity_witness(data,result,result['stats']['original_order'])
     inputs={row['reg']:i-7 for i,row in enumerate(data['instructions'])if row['op']=='GET'}
     for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
      self.assertEqual(interpret(data['instructions'],inputs,semantics),interpret(result['optimized_instructions'],inputs,semantics))
 def test_noncomb_shared_dead_and_memory_rejected(self):
  for family in ('balanced_tree','padded_tree','multi_sink_shared','hazard_multi'):
   self.assertIsNone(recognize_comb_forest(parse_block(generate_workload(7001001,family,128,3))))
  data=generate_workload(7001002,'skew_tree',128,3)
  self.assertIsNone(recognize_comb_forest(parse_block(data,'conservative')))
  data['instructions'].append({'id':len(data['instructions']),'op':'GET','reg':'unused'})
  self.assertIsNone(recognize_comb_forest(parse_block(data)))
