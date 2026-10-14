"""Physical outputs plus isolated queue-contract edge cases, not Level tests."""
import hashlib
import json
from pathlib import Path
from time import perf_counter
import unittest
from unittest.mock import patch

from isa_scheduler.tree_pair_anytime import _Agenda, schedule_fixed_tree_pair_anytime
from scripts.diagnose_tree_dfs_gap import materialize
from scripts.research_spine_age_probe import check

ROOT = Path(__file__).resolve().parents[1]
EMITTED = []


class AnytimePairTests(unittest.TestCase):
    def complete12(self):
        data = json.loads((ROOT/'research/level-stage/tree-subtree-12-input.json').read_text())
        # This single boundary fixture uses independent raw materialization;
        # the40 saved corpus baselines are never recomputed.
        order = list(range(12))
        return data, {'output':materialize(data,order),'original_order':order}

    def propose(self, data, baseline, parent, **options):
        downstream = options.pop('on_completed',None)
        def sink(candidate):
            EMITTED.append({'input':data,'parent':parent,'candidate':candidate})
            if downstream is not None: downstream(candidate)
        return schedule_fixed_tree_pair_anytime(data,baseline,parent,on_completed=sink,**options)

    def test_complete12_preserves_originals_and_finds_zero(self):
        data, baseline = self.complete12()
        self.assertEqual(sum(row['op']=='COPY' for row in baseline['output']['optimized_instructions']),1)
        result = self.propose(data,baseline,10)
        self.assertEqual(result['best']['copies'],0)
        self.assertEqual(result['stats']['outcome'],'exhausted_improvement_search')
        self.assertIsNotNone(result['stats']['first_complete'])
        check(data,result['best']['output'],result['best']['original_order'])

    def test_budget_one_and_tiny_time_retain_original_incumbent(self):
        data,baseline = self.complete12(); snapshot = json.dumps(baseline,sort_keys=True)
        for options in ({'max_states':1},{'time_budget_ms':1e-9}):
            result = self.propose(data,baseline,10,**options)
            self.assertEqual(result['stats']['outcome'],'partial_budget')
            self.assertEqual(result['best']['copies'],1)
            self.assertEqual(len(result['completed_outlets']),0)
            self.assertLessEqual(result['stats']['processed_states'],options.get('max_states',20000))
            self.assertEqual(json.dumps(baseline,sort_keys=True),snapshot)
        limited = self.propose(data,baseline,10,max_states=1)
        self.assertIsNotNone(limited['stats']['unfinished_expansion'])
        self.assertGreater(limited['stats']['actual_open_count'],0)

    def test_goal_interrupted_and_outlet_cap_keep_actual_complete_program(self):
        data,baseline = self.complete12(); expired = [False]
        def clock(): return perf_counter() + (1 if expired[0] else 0)
        def sink(candidate): expired[0] = True
        with patch('isa_scheduler.tree_pair_anytime.perf_counter',clock):
            result = self.propose(data,baseline,10,on_completed=sink)
        self.assertEqual(result['stats']['outcome'],'partial_budget')
        self.assertEqual(result['best']['copies'],0)
        self.assertEqual(len(result['completed_outlets']),1)
        self.assertIsNotNone(result['stats']['unfinished_expansion'])
        check(data,result['best']['output'],result['best']['original_order'])
        capped = self.propose(data,baseline,10,max_outcomes=1)
        self.assertEqual(capped['stats']['outcome'],'partial_outlet_limit')
        self.assertEqual(capped['best']['copies'],0)

    def test_external_unused_multiroot_and_ordered_args(self):
        source = ROOT/'experiments/r163-tree-branch-context-gold'
        cases = [json.loads(line) for line in (source/'inputs.jsonl').read_text().splitlines()]
        case = cases[9]; data = case['input']
        key = hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        baseline = json.loads((source/(key[:16]+'-baseline-output.json')).read_text())
        result = self.propose(data,baseline,case['parent'])
        self.assertEqual(len(result['stats']['external_roles']),1)
        check(data,result['best']['output'],result['best']['original_order'])

    def test_unsupported_hazard_original_copy_bits_and_scope_fail_closed(self):
        data,baseline = self.complete12()
        hazard = json.loads(json.dumps(data)); hazard['instructions'][-1]['reg']='a'
        copy = json.loads(json.dumps(data)); copy['instructions'].append({'id':'original-copy','op':'COPY','source':'t#2'})
        bits = json.loads(json.dumps(data)); bits['bit_width']=1
        for original in (hazard,copy,bits):
            with self.assertRaises(ValueError): self.propose(original,baseline,10)
        with self.assertRaises(ValueError): self.propose(data,baseline,10,max_parent_nodes=1)

    def test_queue_reopen_immutable_path_and_stale_versions(self):
        # Synthetic queue labels test bookkeeping only. They are not physical
        # schedules, empirical performance cases or additional gold inputs.
        agenda = _Agenda(); state = (1,1,(2,1)); old_path = (None,(0,0)); new_path = (None,(1,0))
        agenda.offer(state,10,3,old_path); first = agenda.pop(); agenda.mark_expanded(state,10)
        self.assertTrue(agenda.offer(state,7,3,new_path))
        second = agenda.pop(); self.assertEqual(second[1],7); self.assertEqual(second[3],new_path)
        self.assertEqual(first[3],old_path); self.assertEqual(agenda.reopens,1)
        self.assertFalse(agenda.offer(state,8,3,old_path))
        other = (2,1,(1,3)); agenda.offer(other,12,2,old_path); agenda.offer(other,9,2,new_path)
        self.assertEqual(agenda.pop()[1],9); self.assertIsNone(agenda.pop())
        self.assertEqual(agenda.stale,1); self.assertEqual(agenda.replacements,2)


if __name__ == '__main__': unittest.main()
