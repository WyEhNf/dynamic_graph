import copy,unittest
from isa_scheduler.model import parse_block
from isa_scheduler.root_spines import schedule_root_spines,recognize_root_spines
from isa_scheduler.workloads import generate_workload
from isa_scheduler.verify import verify,IntegerSemantics,interpret
from isa_scheduler.identity_witness import check_identity_witness

class RootSpinesTests(unittest.TestCase):
 def test_complete_stars_fresh_sizes_windows(self):
  for size in (32,128,512,2048):
   for bits in (2,3,4,5):
    for sample in range(3):
     data=generate_workload(6200001+size*13+bits*3+sample,'multi_sink_shared',size,bits)
     output=schedule_root_spines(parse_block(data),time_budget_ms=500)
     verify(data,output);check_identity_witness(data,output,output['stats']['original_order'])
     inputs={row['reg']:17-3*i for i,row in enumerate(data['instructions'])if row['op']=='GET'}
     for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
      self.assertEqual(interpret(data['instructions'],inputs,semantics),interpret(output['optimized_instructions'],inputs,semantics))
 def test_nonmatching_and_memory_hazards_rejected(self):
  for family in ('ladder_diamond','matrix_product_tile','ragged_tree','terminal_root_pairs','cross_group_shared'):
   data=generate_workload(6201001,family,128,3)
   self.assertIsNone(recognize_root_spines(parse_block(data)))
  data=generate_workload(6201002,'multi_sink_shared',128,3)
  self.assertIsNone(recognize_root_spines(parse_block(data,'conservative')))
  hazard=copy.deepcopy(data);hazard['instructions'][-1]['reg']=data['instructions'][0]['reg']
  self.assertIsNone(recognize_root_spines(parse_block(hazard)))
 def test_unbalanced_multiple_groups_duplicate_and_unused_roots(self):
  for seed in range(6400001,6400025):
   for bits in (2,3,4,5):
    data=generate_workload(seed,'unbalanced_root_stars',384,bits)
    output=schedule_root_spines(parse_block(data),time_budget_ms=500)
    verify(data,output);check_identity_witness(data,output,output['stats']['original_order'])
    inputs={row['reg']:11-5*i for i,row in enumerate(data['instructions'])if row['op']=='GET'}
    for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
     self.assertEqual(interpret(data['instructions'],inputs,semantics),interpret(output['optimized_instructions'],inputs,semantics))
