import copy,unittest
from isa_scheduler.model import parse_block,InvalidBlock,BudgetExceeded,InfeasibleSchedule
from isa_scheduler.persistent_cut_bound import persistent_cut_bound,check_persistent_cut_certificate
from isa_scheduler.workloads import generate_workload
from isa_scheduler.fuzz import generate
from isa_scheduler.search import search
from isa_scheduler.optimizer import optimize
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify

class PersistentCutTests(unittest.TestCase):
 def test_raw_copy_can_reference_older_replica_at_window_boundary(self):
  data={'block_id':'older-replica','bit_width':2,'instructions':[
   {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'},{'id':2,'op':'GET','reg':'c'},
   {'id':3,'op':'ADD','inputs':['t#3','t#2']},{'id':4,'op':'ADD','inputs':['t#1','t#2']},
   {'id':5,'op':'SET','reg':'out','inputs':['t#1']}]}
  output={'block_id':data['block_id'],'optimized_instructions':[
   {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'COPY','source':'t#1'},
   {'id':2,'op':'GET','reg':'b'},{'id':3,'op':'GET','reg':'c'},
   # COPY references original position zero (d_used=4), although position one
   # is a newer replica (d_latest=3). Both are legal identity-preserving sources.
   {'id':4,'op':'COPY','source':'t#4'},{'id':5,'op':'ADD','inputs':['t#1','t#3']},
   {'id':6,'op':'ADD','inputs':['t#1','t#3']},{'id':7,'op':'SET','reg':'out','inputs':['t#1']}]}
  verify(data,output);proof=check_identity_witness(data,output,list(range(6)))
  self.assertEqual(proof['verified_inserted_copies'],2)
 def test_ladder_large_and_certificate_tampering(self):
  for bits in (2,3,4,5):
   data=generate_workload(7200001,'ladder_diamond',256,bits)
   certificate=persistent_cut_bound(parse_block(data),time_budget_ms=2000)
   self.assertIsNotNone(certificate)
   proof=check_persistent_cut_certificate(data,certificate)
   result=optimize(data,time_budget_ms=1000)
   self.assertLessEqual(proof['verified_global_copy_lower_bound'],result['stats']['inserted_copy_count'])
   broken=copy.deepcopy(certificate);broken['witness']['forced_inner_nodes']+=1
   with self.assertRaises(InvalidBlock):check_persistent_cut_certificate(data,broken)
 def test_fresh_small_full_age_oracle(self):
  compared=0
  for index in range(240):
   data=generate(7300001+index,('wide','branch','highfanout')[index%3],2+index%4)
   block=parse_block(data);certificate=persistent_cut_bound(block,time_budget_ms=1000)
   if not certificate:continue
   proof=check_persistent_cut_certificate(data,certificate)
   try:result=search(block,time_budget_ms=2000,max_states=1000000,beam_width=None)
   except BudgetExceeded:continue
   except InfeasibleSchedule:continue
   self.assertEqual(result['stats']['search']['outcome'],'optimal_under_model')
   self.assertLessEqual(proof['verified_global_copy_lower_bound'],result['stats']['inserted_copy_count']);compared+=1
  self.assertGreater(compared,2)
