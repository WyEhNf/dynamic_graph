import copy,random,unittest
from isa_scheduler.consumer_copy_bound import consumer_copy_bound,check_consumer_copy_certificate
from isa_scheduler.model import parse_block,InvalidBlock
from isa_scheduler.scheduler import InfeasibleSchedule
from isa_scheduler.search import search
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


class ConsumerCopyBoundTests(unittest.TestCase):
    def test_240_small_pure_graphs_against_complete_age_state_oracle(self):
        feasible=positive=0
        for seed in range(240):
            rng=random.Random(seed);roots=1 if seed%2==0 else 2
            rows=[{'id':i,'op':'GET','reg':f'r{i}'}for i in range(roots)]
            length=rng.randrange(5,8)
            for _ in range(length):
                index=len(rows)
                sources=(0,index-1) if seed%3==0 else (rng.randrange(index),rng.randrange(index))
                rows.append({'id':index,'op':rng.choice(('ADD','MULW')),'inputs':[f't#{index-source}'for source in sources]})
            rows.append({'id':len(rows),'op':'SET','reg':'out','inputs':['t#1']})
            data={'block_id':seed,'bit_width':2,'instructions':rows};block=parse_block(data)
            bound=consumer_copy_bound(block);raw=check_consumer_copy_certificate(data,bound)
            self.assertEqual(raw['verified_global_copy_lower_bound'],bound['copy_lower_bound'])
            positive+=bound['copy_lower_bound']>0
            try:result=search(block,time_budget_ms=2000,max_states=200000)
            except InfeasibleSchedule:continue
            self.assertEqual(result['stats']['search']['outcome'],'optimal_under_model')
            self.assertLessEqual(bound['copy_lower_bound'],result['stats']['inserted_copy_count'])
            verify(data,result);feasible+=1
        self.assertGreater(feasible,200);self.assertGreater(positive,20)

    def test_repeated_operand_counts_one_consumer_and_scope_screens(self):
        rows=[{'id':0,'op':'GET','reg':'r'}]
        for index in range(1,5):rows.append({'id':index,'op':'ADD','inputs':[f't#{index}',f't#{index}']})
        data={'block_id':'repeat','bit_width':2,'instructions':rows}
        bound=consumer_copy_bound(parse_block(data));self.assertEqual(bound['copy_lower_bound'],0)
        rows.append({'id':5,'op':'ADD','inputs':['t#5','t#5']})
        bound=consumer_copy_bound(parse_block(data));self.assertEqual(bound['copy_lower_bound'],1)
        self.assertEqual(check_consumer_copy_certificate(data,bound)['verified_global_copy_lower_bound'],1)
        for family in ('multi_sink_shared','multi_sink_irregular'):
            pure=generate_workload(41,family,1024,4);proposal=consumer_copy_bound(parse_block(pure))
            self.assertGreater(proposal['copy_lower_bound'],0)
            self.assertEqual(check_consumer_copy_certificate(pure,proposal)['verified_global_copy_lower_bound'],proposal['copy_lower_bound'])
        copy_input=copy.deepcopy(data);copy_input['instructions'][1]={'id':1,'op':'COPY','source':'t#1'}
        self.assertIsNone(consumer_copy_bound(parse_block(copy_input)))
        with self.assertRaises(InvalidBlock):check_consumer_copy_certificate(copy_input,bound)
        hazard=generate_workload(41,'hazard_multi',128,3)
        self.assertIsNone(consumer_copy_bound(parse_block(hazard)))
        with self.assertRaises(InvalidBlock):check_consumer_copy_certificate(hazard,bound)

    def test_independent_raw_grammar_and_forged_bound_rejected(self):
        data=generate_workload(41,'multi_sink_shared',1024,4);bound=consumer_copy_bound(parse_block(data))
        for kind in ('unknown_op','unknown_field','future_ref','duplicate_id','bool_id','bad_arity','bad_register','noncanonical_ref','same_reg'):
            invalid=copy.deepcopy(data)
            if kind=='unknown_op':invalid['instructions'][0]['op']='PUT'
            elif kind=='unknown_field':invalid['instructions'][0]['extra']=1
            elif kind=='future_ref':invalid['instructions'][-1]['inputs']=['t#9999999']
            elif kind=='duplicate_id':invalid['instructions'][1]['id']=invalid['instructions'][0]['id']
            elif kind=='bool_id':invalid['instructions'][0]['id']=False
            elif kind=='bad_arity':invalid['instructions'][-1]['inputs']=[]
            elif kind=='bad_register':invalid['instructions'][0]['reg']=False
            elif kind=='noncanonical_ref':invalid['instructions'][-1]['inputs']=['t#01']
            else:invalid['instructions'][-1]['reg']=invalid['instructions'][0]['reg']
            with self.assertRaises(InvalidBlock):check_consumer_copy_certificate(invalid,bound)
        for bad in ({**bound,'window':8},{**bound,'copy_lower_bound':True},{**bound,'copy_lower_bound':bound['copy_lower_bound']+1}):
            with self.assertRaises(InvalidBlock):check_consumer_copy_certificate(data,bad)
