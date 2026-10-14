import json
from pathlib import Path
from time import perf_counter
import unittest
from unittest.mock import patch

from isa_scheduler.tree_pair_refine import refine_fixed_tree_pairs
from scripts.diagnose_tree_dfs_gap import materialize
from scripts.research_spine_age_probe import check

ROOT=Path(__file__).resolve().parents[1]
EMITTED=[]


class TreePairRefineTests(unittest.TestCase):
    def fixture(self):
        data=json.loads((ROOT/'research/level-stage/tree-subtree-12-input.json').read_text())
        order=list(range(12)); return data,{'output':materialize(data,order),'original_order':order}

    def sink(self,data):
        def save(parent,candidate): EMITTED.append({'input':data,'parent':parent,'candidate':candidate})
        return save

    def test_total_state_budget_and_incumbent_retention(self):
        data,baseline=self.fixture(); before=json.dumps(baseline,sort_keys=True)
        result=refine_fixed_tree_pairs(data,baseline,max_states=1,on_completed=self.sink(data))
        self.assertEqual(result['stats']['outcome'],'partial_budget')
        self.assertEqual(result['stats']['processed_states'],1)
        self.assertEqual(result['best']['copies'],1)
        self.assertEqual(json.dumps(baseline,sort_keys=True),before)
        check(data,result['best']['output'],result['best']['original_order'])

    def test_prepare_timeout_retains_original(self):
        data,baseline=self.fixture()
        result=refine_fixed_tree_pairs(data,baseline,time_budget_ms=1e-9,on_completed=self.sink(data))
        self.assertEqual(result['stats']['outcome'],'partial_budget')
        self.assertEqual(result['stats']['processed_states'],0)
        self.assertEqual(result['best']['copies'],1)

    def test_complete_output_survives_injected_deadline(self):
        data,baseline=self.fixture(); expired=[False]; save=self.sink(data)
        def clock(): return perf_counter()+(1 if expired[0] else 0)
        def sink(parent,candidate): save(parent,candidate); expired[0]=True
        with patch('isa_scheduler.tree_pair_refine.perf_counter',clock),patch('isa_scheduler.tree_subtree_interleave.perf_counter',clock):
            result=refine_fixed_tree_pairs(data,baseline,on_completed=sink)
        self.assertEqual(result['stats']['outcome'],'partial_budget')
        self.assertEqual(result['stats']['complete_outputs'],1)
        self.assertEqual(result['best']['copies'],0)
        check(data,result['best']['output'],result['best']['original_order'])


if __name__=='__main__': unittest.main()
