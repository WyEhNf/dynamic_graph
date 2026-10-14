import copy,unittest
from isa_scheduler.workloads import generate_workload
from isa_scheduler.model import parse_block,InvalidBlock,InfeasibleSchedule
from isa_scheduler.reduction_columns import recognize_reduction_columns,schedule_reduction_columns
from isa_scheduler.reduction_copy_bound import reduction_copy_bound,check_reduction_copy_certificate
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify,IntegerSemantics,interpret

class ReductionColumnTests(unittest.TestCase):
 def test_exact_roles_and_bounded_window_outputs(self):
  for bits in(3,4,5):
   data=generate_workload(7910041,'dot_product_many',512,bits);block=parse_block(data)
   result=schedule_reduction_columns(block,time_budget_ms=1000)
   verify(data,result);check_identity_witness(data,result,result['stats']['original_order'])
   initial={r['reg']:i*19-13 for i,r in enumerate(data['instructions'])if r['op']=='GET'}
   for semantics in(IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
    self.assertEqual(interpret(data['instructions'],initial,semantics),interpret(result['optimized_instructions'],initial,semantics))
   if bits>=4:self.assertEqual(result['stats']['inserted_copy_count'],0)
   certificate=reduction_copy_bound(block)
   if certificate:self.assertLessEqual(check_reduction_copy_certificate(data,certificate)['verified_global_copy_lower_bound'],result['stats']['inserted_copy_count'])
 def test_complete_structure_rejects_unknown_extra_or_aliased_rows(self):
  original=generate_workload(7910042,'dot_product_many',128,3)
  bad=copy.deepcopy(original);bad['instructions'][1]['reg']=bad['instructions'][0]['reg']
  self.assertIsNone(recognize_reduction_columns(parse_block(bad)))
  bad=copy.deepcopy(original);bad['instructions'].append({'id':len(bad['instructions']),'op':'GET','reg':'extra'})
  self.assertIsNone(recognize_reduction_columns(parse_block(bad)))
  self.assertIsNone(recognize_reduction_columns(parse_block(generate_workload(7910043,'dot_product_many',128,2))))
 def test_independent_age_certificate_tampering(self):
  data=generate_workload(7910044,'dot_product_many',4096,3);certificate=reduction_copy_bound(parse_block(data))
  self.assertIsNotNone(certificate);self.assertGreater(check_reduction_copy_certificate(data,certificate)['verified_global_copy_lower_bound'],0)
  bad=copy.deepcopy(certificate);bad['witness']['rows'][1]['private'][0]=bad['witness']['rows'][0]['private'][0]
  with self.assertRaises(InvalidBlock):check_reduction_copy_certificate(data,bad)
  bad=copy.deepcopy(certificate);bad['witness']['forced_nonrefresh_originals']+=1
  with self.assertRaises(InvalidBlock):check_reduction_copy_certificate(data,bad)
