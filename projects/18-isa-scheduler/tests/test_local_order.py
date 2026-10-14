import unittest
from time import perf_counter
from isa_scheduler.fuzz import generate
from isa_scheduler.model import parse_block,InfeasibleSchedule,BudgetExceeded
from isa_scheduler.local_order import emit_order,improve_order
from isa_scheduler.incremental import schedule_incremental
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import verify,IntegerSemantics,interpret


class LocalOrderTests(unittest.TestCase):
    def test_300_fresh_graphs_simulated_and_materialized_match(self):
        for seed in range(300):
            data=generate(seed,('wide','branch','highfanout','hazard')[seed%4],2+seed%4)
            block=parse_block(data);order=list(range(len(block.instructions)));deadline=perf_counter()+2
            try:old=schedule_incremental(block,'stable_fast')
            except InfeasibleSchedule:
                self.assertIsNone(emit_order(block,order,deadline=deadline));continue
            emitted=emit_order(block,order,deadline=deadline)
            self.assertEqual(old['optimized_instructions'],emitted['optimized_instructions'])
            self.assertEqual(emit_order(block,order,deadline=deadline,materialize=False),old['stats']['inserted_copy_count'])
            new=improve_order(data,block,old,time_budget_ms=50,neighborhood='relocate' if seed%2 else 'adjacent')
            self.assertLessEqual(new['stats']['inserted_copy_count'],old['stats']['inserted_copy_count'])
            verify(data,new)
            initial={node.reg:7+node.index*3 for node in block.instructions if node.op=='GET'}
            for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False)):
                self.assertEqual(interpret(data['instructions'],initial,semantics),interpret(new['optimized_instructions'],initial,semantics))

    def test_dependencies_hazards_duplicates_and_dead_nodes(self):
        data={'block_id':'hazard','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'r'}, {'id':1,'op':'SET','reg':'r','inputs':['t#1']},
            {'id':2,'op':'GET','reg':'r'}, {'id':3,'op':'COPY','source':'t#1'},
            {'id':4,'op':'ADD','inputs':['t#1','t#1']}]}
        block=parse_block(data)
        for invalid in ([0,2,1,3,4],[0,1,3,2,4],[0,1,2,3,3]):
            with self.assertRaises(ValueError):emit_order(block,invalid,deadline=perf_counter()+1)
        good=emit_order(block,list(range(5)),deadline=perf_counter()+1);verify(data,good)
        self.assertEqual(good['stats']['total_copy_count'],1)

    def test_budget_retains_verified_candidate_and_untrusted_incumbent_rejected(self):
        data=generate(101,'branch',2);block=parse_block(data);old=optimize(data,time_budget_ms=500)
        tiny=improve_order(data,block,old,time_budget_ms=0.000001);verify(data,tiny)
        self.assertLessEqual(tiny['stats']['inserted_copy_count'],old['stats']['inserted_copy_count'])
        bad={**old,'optimized_instructions':[{'id':0,'op':'PUT'}]}
        with self.assertRaises(ValueError):improve_order(data,block,bad)
        with self.assertRaises(BudgetExceeded):emit_order(block,list(range(len(block.instructions))),deadline=0)

    def test_public_strategy_and_size_cap(self):
        data=generate(31,'highfanout',4);new=optimize(data,'local_swap',time_budget_ms=100)
        verify(data,new);self.assertEqual(new['stats']['requested_strategy'],'local_swap')
        capped=improve_order(data,parse_block(data),new,max_nodes=1)
        self.assertEqual(capped['stats']['local_order']['outcome'],'skipped_size_or_zero_copy')
        moved=optimize(data,'local_relocate',time_budget_ms=100);verify(data,moved)
        self.assertEqual(moved['stats']['requested_strategy'],'local_relocate')
