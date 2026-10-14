import random,unittest
from isa_scheduler.spine_copy_bound import spine_copy_bound,check_spine_copy_certificate
from isa_scheduler.model import InvalidBlock
import copy
from isa_scheduler.model import parse_block
from isa_scheduler.search import search
from isa_scheduler.workloads import generate_workload
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import verify


class SpineCopyBoundTests(unittest.TestCase):
    def test_200_small_forced_spines_against_full_original_copy_oracle(self):
        positive=0
        for seed in range(200):
            rng=random.Random(seed);rows=[{'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'}]
            length=rng.randint(4,7)
            for stage in range(length):
                index=len(rows);sources=(0,1) if not stage else (index-1,rng.randrange(2))
                rows.append({'id':index,'op':rng.choice(('ADD','MULW')),'inputs':[f't#{index-source}'for source in sources]})
            rows.append({'id':len(rows),'op':'SET','reg':'out','inputs':['t#1']})
            data={'block_id':seed,'bit_width':2,'instructions':rows};block=parse_block(data)
            bound=spine_copy_bound(block)['copy_lower_bound'];positive+=bool(bound)
            oracle=search(block,time_budget_ms=1000,max_states=200000)
            self.assertEqual(oracle['stats']['search']['outcome'],'optimal_under_model')
            self.assertLessEqual(bound,oracle['stats']['inserted_copy_count']);verify(data,oracle)
        self.assertGreater(positive,0)

    def test_large_near_window_bound_and_screening(self):
        data=generate_workload(11,'near_window_spine',1024,5)
        block=parse_block(data);bound=spine_copy_bound(block);result=optimize(data,time_budget_ms=2000)
        self.assertGreater(bound['copy_lower_bound'],10000)
        self.assertLessEqual(bound['copy_lower_bound'],result['stats']['inserted_copy_count'])
        self.assertEqual(check_spine_copy_certificate(data,bound)['verified_global_copy_lower_bound'],bound['copy_lower_bound'])
        bad=copy.deepcopy(bound);bad['witness']['forced_inner_steps']+=1
        with self.assertRaises(InvalidBlock):check_spine_copy_certificate(data,bad)
        for kind in ('unknown_op','unknown_field','future_ref','duplicate_id','bad_arity','bad_register','noncanonical_ref'):
            invalid=copy.deepcopy(data)
            if kind=='unknown_op':invalid['instructions'][0]['op']='PUT'
            elif kind=='unknown_field':invalid['instructions'][0]['extra']=1
            elif kind=='future_ref':invalid['instructions'][len([r for r in invalid['instructions'] if r['op']=='GET'])]['inputs'][0]='t#999999'
            elif kind=='duplicate_id':invalid['instructions'][1]['id']=invalid['instructions'][0]['id']
            elif kind=='bad_arity':invalid['instructions'][-1]['inputs']=[]
            elif kind=='bad_register':invalid['instructions'][0]['reg']=False
            else:invalid['instructions'][-1]['inputs']=['t#01']
            with self.assertRaises(InvalidBlock):check_spine_copy_certificate(invalid,bound)
        bad={**bound,'copy_lower_bound':result['stats']['inserted_copy_count']+1000}
        with self.assertRaises(InvalidBlock):check_spine_copy_certificate(data,bad)
        for family in ('multi_sink_shared','hazard_multi','butterfly'):
            self.assertIsNone(spine_copy_bound(parse_block(generate_workload(11,family,128,4))))
