import copy,unittest
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.workloads import FAMILIES,generate_workload
from isa_scheduler.optimizer import optimize
from isa_scheduler.model import InvalidBlock,InfeasibleSchedule,BudgetExceeded
from isa_scheduler.verify import verify


class IdentityWitnessTests(unittest.TestCase):
    def test_all_21_families_and_four_windows_128_fresh_graphs(self):
        success=0
        for seed in range(128):
            data=generate_workload(4700001+seed,FAMILIES[seed%len(FAMILIES)],64,2+seed%4)
            try:output=optimize(data,time_budget_ms=500)
            except (InfeasibleSchedule,BudgetExceeded):continue
            proof=check_identity_witness(data,output,output['stats']['original_order'])
            self.assertEqual(proof['verified_original_identities'],len(data['instructions']))
            self.assertEqual(proof['verified_inserted_copies'],output['stats']['inserted_copy_count']);verify(data,output);success+=1
        self.assertGreater(success,80)

    def test_semantically_equal_alias_reference_fails_exact_identity(self):
        data={'block_id':'aliases','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'a'},
            {'id':1,'op':'ADD','inputs':['t#1','t#1']},
            {'id':2,'op':'ADD','inputs':['t#2','t#2']},
            {'id':3,'op':'SET','reg':'out','inputs':['t#1']}]}
        good={'block_id':'aliases','optimized_instructions':copy.deepcopy(data['instructions'])}
        check_identity_witness(data,good,[0,1,2,3]);verify(data,good)
        aliased=copy.deepcopy(good);aliased['optimized_instructions'][-1]['inputs']=['t#2']
        verify(data,aliased)  # Mathematical expressions equal; original IDs differ.
        with self.assertRaises(InvalidBlock):check_identity_witness(data,aliased,[0,1,2,3])
        for order in ([0,1,1,3],[True,1,2,3],[0,1,2],[-1,1,2,3]):
            with self.assertRaises(InvalidBlock):check_identity_witness(data,good,order)

    def test_same_register_hazard_order_and_strict_rejection(self):
        data={'block_id':'hazard','bit_width':2,'instructions':[{'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'a'},{'id':2,'op':'SET','reg':'a','inputs':['t#2']}]}
        out={'block_id':'hazard','optimized_instructions':copy.deepcopy(data['instructions'])}
        check_identity_witness(data,out,[0,1,2])
        swapped=copy.deepcopy(out);swapped['optimized_instructions'][-1]['inputs']=['t#1']
        check_identity_witness(data,swapped,[1,0,2])  # Read/read is not a hazard.
        with self.assertRaises(InvalidBlock):check_identity_witness(data,swapped,[1,0,2],memory_order='conservative')
        crossing={'block_id':'hazard','bit_width':2,'instructions':[{'id':0,'op':'GET','reg':'a'},{'id':1,'op':'SET','reg':'a','inputs':['t#1']},{'id':2,'op':'GET','reg':'a'}]}
        reordered={'block_id':'hazard','optimized_instructions':[{'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'a'},{'id':2,'op':'SET','reg':'a','inputs':['t#2']}]}
        with self.assertRaises(InvalidBlock):check_identity_witness(crossing,reordered,[0,2,1])
        for kind in ('PUT','bool_id','unknown_field','current_ref','future_ref','wide_ref'):
            bad=copy.deepcopy(out)
            if kind=='PUT':bad['optimized_instructions'][0]['op']='PUT'
            elif kind=='bool_id':bad['optimized_instructions'][0]['id']=False
            elif kind=='unknown_field':bad['optimized_instructions'][0]['extra']=0
            else:bad['optimized_instructions'][-1]['inputs']=[{'current_ref':'t#0','future_ref':'t#999','wide_ref':'t#5'}[kind]]
            with self.assertRaises(InvalidBlock):check_identity_witness(data,bad,[0,1,2])
        copy_input={'block_id':0,'bit_width':2,'instructions':[{'id':0,'op':'GET','reg':'a'},{'id':1,'op':'COPY','source':'t#1'}]}
        with self.assertRaises(InvalidBlock):check_identity_witness(copy_input,{'block_id':0,'optimized_instructions':copy_input['instructions']},[0,1])
