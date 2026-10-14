import copy,random,unittest
from isa_scheduler.model import parse_block,InvalidBlock
from isa_scheduler.search import search
from isa_scheduler.pair_copy_bound import pair_copy_bound,check_pair_copy_certificate
from isa_scheduler.consumer_copy_bound import consumer_copy_bound
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload


class PairCopyBoundTests(unittest.TestCase):
    def test_adjacent_root_computations_use_next_position_age_coordinates(self):
        for count in (1,2,3,4):
            rows=[{'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'}]
            for index in range(2,count+2):rows.append({'id':index,'op':'ADD','inputs':[f't#{index}',f't#{index-1}']})
            for value in range(2,count+2):rows.append({'id':len(rows),'op':'SET','reg':f'out{value}','inputs':[f't#{len(rows)-value}']})
            data={'block_id':count,'bit_width':2,'instructions':rows};block=parse_block(data)
            # At ADD position2, ages are2/1; at next position3 they are3/2.
            bound=pair_copy_bound(block)
            if count<=3:self.assertIsNone(bound)
            else:
                self.assertEqual(bound['copy_lower_bound'],2)
                self.assertEqual(check_pair_copy_certificate(data,bound)['verified_global_copy_lower_bound'],2)
            oracle=search(block,time_budget_ms=2000,max_states=200000)
            self.assertEqual(oracle['stats']['inserted_copy_count'],0 if count<=3 else 2)

    def test_60_terminal_groups_against_complete_oracle_up_to_14_nodes(self):
        positive=0
        for seed in range(60):
            rng=random.Random(seed);count=2+seed%5
            rows=[{'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'}]
            for index in range(2,count+2):
                operands=[f't#{index}',f't#{index-1}'];rng.shuffle(operands)
                rows.append({'id':index,'op':rng.choice(('ADD','MULW')),'inputs':operands})
            values=list(range(2,count+2));rng.shuffle(values)
            for store,value in enumerate(values):
                rows.append({'id':len(rows),'op':'SET','reg':f'o{store}','inputs':[f't#{len(rows)-value}']})
            data={'block_id':seed,'bit_width':2,'instructions':rows};block=parse_block(data)
            bound=pair_copy_bound(block)
            result=search(block,time_budget_ms=2000,max_states=200000,exact_max_nodes=14)
            self.assertEqual(result['stats']['search']['outcome'],'optimal_under_model');verify(data,result)
            if bound:
                positive+=1
                self.assertLessEqual(bound['copy_lower_bound'],result['stats']['inserted_copy_count'])
                # For these isolated W=4 two-root stars, the endpoint bound
                # equals the complete oracle; this is not a general theorem.
                self.assertEqual(bound['copy_lower_bound'],result['stats']['inserted_copy_count'])
                self.assertEqual(check_pair_copy_certificate(data,bound)['verified_global_copy_lower_bound'],bound['copy_lower_bound'])
        self.assertGreater(positive,20)

    def test_new_large_group_and_witness_tamper(self):
        data=generate_workload(455,'terminal_root_pairs',1024,2);bound=pair_copy_bound(parse_block(data))
        self.assertIsNotNone(bound)
        self.assertGreater(bound['copy_lower_bound'],consumer_copy_bound(parse_block(data))['copy_lower_bound'])
        self.assertEqual(check_pair_copy_certificate(data,bound)['verified_global_copy_lower_bound'],bound['copy_lower_bound'])
        for kind in ('count','roots','reuse','claimed','window'):
            bad=copy.deepcopy(bound)
            if kind=='count':bad['pairs'][0]['terminal_computations']+=1
            elif kind=='roots':bad['pairs'][0]['roots']=[0,0]
            elif kind=='reuse':bad['pairs'].append(bad['pairs'][0])
            elif kind=='claimed':bad['copy_lower_bound']+=1
            else:bad['window']=8
            with self.assertRaises(InvalidBlock):check_pair_copy_certificate(data,bad)
        hazard=copy.deepcopy(data);hazard['instructions'][-1]['reg']=hazard['instructions'][0]['reg']
        self.assertIsNone(pair_copy_bound(parse_block(hazard)))
        with self.assertRaises(InvalidBlock):check_pair_copy_certificate(hazard,bound)
