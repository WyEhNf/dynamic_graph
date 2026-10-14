import copy
import unittest
from experiments.baseline_r40.isa_scheduler.verify import inspect as old_inspect
from isa_scheduler.verify import inspect,verify
from isa_scheduler.optimizer import optimize
from isa_scheduler.model import InvalidBlock
from isa_scheduler.workloads import generate_workload


class WindowVerifierTests(unittest.TestCase):
    def test_window_ring_matches_frozen_full_history(self):
        for seed in range(120):
            bits=2+seed%4
            data=generate_workload(seed,'serial_chains' if seed%2 else 'near_window_spine',64,bits)
            result=optimize(data,time_budget_ms=1000)
            rows=result['optimized_instructions']
            self.assertEqual(inspect(rows,1<<bits,contiguous_ids=True),old_inspect(rows,1<<bits,contiguous_ids=True))
            self.assertEqual(inspect(data['instructions']),old_inspect(data['instructions']))

    def test_contiguous_ids_and_window_still_strict(self):
        rows=[{'id':0,'op':'GET','reg':'r'}]
        for _ in range(100):rows.append({'id':len(rows),'op':'COPY','source':'t#1'})
        rows.append({'id':len(rows),'op':'SET','reg':'out','inputs':['t#4']})
        self.assertEqual(inspect(rows,4,contiguous_ids=True),old_inspect(rows,4,contiguous_ids=True))
        for index,field,value in ((0,'id',False),(10,'id',9),(10,'source','t#5'),(0,'source','t#1')):
            bad=copy.deepcopy(rows);bad[index][field]=value
            with self.assertRaises(InvalidBlock):inspect(bad,4,contiguous_ids=True)
        with self.assertRaises(InvalidBlock):inspect([],0)
        self.assertEqual(inspect([],32),old_inspect([],32))

    def test_boundary_early_future_ids_and_register_writes(self):
        rows=[{'id':0,'op':'GET','reg':'r'}]
        for _ in range(50):
            rows.extend(({'id':len(rows),'op':'ADD','inputs':['t#1','t#1']},
                         {'id':len(rows)+1,'op':'SET','reg':'r','inputs':['t#1']},
                         {'id':len(rows)+2,'op':'GET','reg':'r'}))
        self.assertEqual(inspect(rows,4,contiguous_ids=True),old_inspect(rows,4,contiguous_ids=True))
        original={'block_id':'writes','bit_width':2,'instructions':rows}
        verify(original,{'block_id':'writes','optimized_instructions':rows})
        for index,field,value in ((0,'id',100),(1,'id',3),(1,'inputs',['t#4','t#1']),
                                 (1,'inputs',['t#0','t#1']),(1,'inputs',['t#-1','t#1']),
                                 (2,'op','PUT'),(2,'reg','other')):
            bad=copy.deepcopy(rows);bad[index][field]=value
            with self.assertRaises(InvalidBlock):verify(original,{'block_id':'writes','optimized_instructions':bad})
