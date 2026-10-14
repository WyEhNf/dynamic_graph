import unittest
from experiments.baseline_r51.isa_scheduler.incremental import schedule_incremental as old_schedule
from isa_scheduler.incremental import schedule_incremental
from isa_scheduler.fuzz import generate
from isa_scheduler.workloads import FAMILIES,generate_workload
from isa_scheduler.model import parse_block,InfeasibleSchedule
from isa_scheduler.verify import verify


class StableOrderTests(unittest.TestCase):
    def compare(self,data,memory_order='hazard',factor=None):
        block=parse_block(data,memory_order)
        try:old=old_schedule(block,'stable_fast',max_copy_factor=factor)
        except Exception as exc:
            self.assertEqual(type(exc).__name__,'InfeasibleSchedule')
            with self.assertRaises(InfeasibleSchedule):schedule_incremental(block,'stable_fast',max_copy_factor=factor)
        else:
            new=schedule_incremental(block,'stable_fast',max_copy_factor=factor)
            self.assertEqual(new['optimized_instructions'],old['optimized_instructions'])
            self.assertEqual(new['stats']['inserted_copy_count'],old['stats']['inserted_copy_count'])
            verify(data,new)

    def test_800_small_graphs_and_register_hazards_exactly_match(self):
        for seed in range(800):
            data=generate(seed,('wide','branch','highfanout','hazard')[seed%4],2+seed%4)
            self.compare(data)
            if seed%10==0:self.compare(data,'conservative')

    def test_all_large_shapes_and_explicit_copy_guard(self):
        for family in FAMILIES:
            for bits in range(2,6):self.compare(generate_workload(100,family,128,bits))
        data=generate_workload(10,'near_window_spine',512,5)
        self.compare(data)
        self.compare(data,factor=8)

    def test_original_copy_and_duplicate_operands(self):
        data={'block_id':'copy','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'r'},{'id':1,'op':'COPY','source':'t#1'},
            {'id':2,'op':'ADD','inputs':['t#2','t#1']},{'id':3,'op':'SET','reg':'r','inputs':['t#1']},
            {'id':4,'op':'GET','reg':'r'},{'id':5,'op':'ADD','inputs':['t#1','t#1']}]}
        self.compare(data)
