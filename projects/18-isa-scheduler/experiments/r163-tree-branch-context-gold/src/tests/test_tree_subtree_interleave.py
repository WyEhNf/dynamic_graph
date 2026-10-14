import json
from pathlib import Path
import unittest
from unittest.mock import patch
from time import perf_counter

from isa_scheduler.model import BudgetExceeded
from isa_scheduler.tree_subtree_interleave import schedule_fixed_tree_pair
from scripts.diagnose_tree_dfs_gap import materialize
from scripts.research_spine_age_probe import check
from scripts.tree_branch_context_cases import generated

ROOT=Path(__file__).resolve().parents[1]
EMITTED=[]


class TreeSubtreeTests(unittest.TestCase):
    def incumbent(self,data,order):
        return {'output':materialize(data,order),'original_order':order}

    def propose(self,data,baseline,parent,**options):
        downstream=options.pop('on_completed',None)
        def sink(candidate):
            EMITTED.append({'input':data,'parent':parent,'candidate':candidate})
            if downstream is not None: downstream(candidate)
        return schedule_fixed_tree_pair(data,baseline,parent,on_completed=sink,**options)

    def test_complete12_counterexample(self):
        data=json.loads((ROOT/'research/level-stage/tree-subtree-12-input.json').read_text())
        baseline=self.incumbent(data,list(range(12)))
        self.assertEqual(sum(row['op']=='COPY' for row in baseline['output']['optimized_instructions']),1)
        result=self.propose(data,baseline,10)
        self.assertEqual(result['best']['copies'],0)
        check(data,result['best']['output'],result['best']['original_order'])

    def test_external_unused_and_multiple_roots(self):
        case=generated(9); data=case['input']; baseline=self.incumbent(data,case['baseline_order'])
        result=self.propose(data,baseline,case['parent'])
        self.assertEqual(len(result['stats']['external_roles']),1)
        for candidate in result['completed_outlets']: check(data,candidate['output'],candidate['original_order'])

    def test_unsupported_copy_hazard_and_bits_fail_closed(self):
        case=generated(0); data=case['input']; baseline=self.incumbent(data,case['baseline_order'])
        hazard=json.loads(json.dumps(data)); hazard['instructions'][-1]['reg']='left_a'
        with self.assertRaises(ValueError): self.propose(hazard,baseline,case['parent'])
        copy=json.loads(json.dumps(data)); copy['instructions'].append({'id':'original-copy','op':'COPY','source':'t#2'})
        with self.assertRaises(ValueError): self.propose(copy,baseline,case['parent'])
        bits=json.loads(json.dumps(data)); bits['bit_width']=1
        with self.assertRaises(ValueError): self.propose(bits,baseline,case['parent'])

    def test_real_state_time_budget_and_completed_sink(self):
        case=generated(9); data=case['input']; baseline=self.incumbent(data,case['baseline_order'])
        for options in ({'max_states':1},{'time_budget_ms':1e-9}):
            with self.assertRaises(BudgetExceeded): self.propose(data,baseline,case['parent'],**options)
        # Deterministic deadline injection after one real complete outlet.
        # This tests preservation, not a measured performance timeout claim.
        completed=[]; expired=[False]
        def clock(): return perf_counter()+(1 if expired[0] else 0)
        def sink(candidate): completed.append(candidate); expired[0]=True
        with patch('isa_scheduler.tree_subtree_interleave.perf_counter',clock):
            with self.assertRaises(BudgetExceeded): self.propose(data,baseline,case['parent'],on_completed=sink)
        self.assertEqual(len(completed),1)
        check(data,completed[0]['output'],completed[0]['original_order'])


if __name__=='__main__': unittest.main()
