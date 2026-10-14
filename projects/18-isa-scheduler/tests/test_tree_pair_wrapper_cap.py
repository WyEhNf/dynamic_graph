"""Synthetic wrapper dispatch contracts, not physical pair-family claims.

Each sink actually receives a full saved witness, checked by the producer.
Child state/frontier counters are synthetic; saved21 is deliberately not
claimed to belong to the mocked parent family or to be a new search gain.
"""
import json
from pathlib import Path
from time import perf_counter
import unittest
from unittest.mock import patch

from isa_scheduler.tree_pair_anytime_refine import refine_fixed_tree_pairs_anytime

ROOT=Path(__file__).resolve().parents[1]
EMITTED=[]
RETURNS=[]


class WrapperCapTests(unittest.TestCase):
    def fixtures(self):
        source=ROOT/'experiments/r172-tree-pair-anytime-84'; key='ca93bf4ab93ad824'
        data=None
        # Look up by canonical SHA instead of assuming source corpus order.
        import hashlib
        for line in (source/'inputs.jsonl').read_text().splitlines():
            candidate=json.loads(line)['input']
            digest=hashlib.sha256(json.dumps(candidate,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            if digest.startswith(key): data=candidate; break
        self.assertIsNotNone(data)
        baseline=json.loads((source/(key+'-baseline-output.json')).read_text())
        better=json.loads((source/(key+'-dp-actual-output.json')).read_text())
        better['copies']=sum(row['op']=='COPY' for row in better['output']['optimized_instructions'])
        baseline['copies']=sum(row['op']=='COPY' for row in baseline['output']['optimized_instructions'])
        return data,baseline,better

    def run_contract(self,mode):
        data,baseline,better=self.fixtures(); calls=[]; expired=[False]
        def child(original,initial,parent,**options):
            self.assertIs(original,data); self.assertIs(initial,baseline)
            self.assertEqual(options['max_outcomes'],16); self.assertEqual(options['max_parent_nodes'],96)
            if calls: self.assertEqual(options['absolute_deadline'],calls[0]['absolute_deadline'])
            index=len(calls); calls.append({'parent':parent, 'remaining_states':options['max_states'],
                                            'absolute_deadline':options['absolute_deadline']})
            outcome='exhausted_improvement_search'; used=0; sent=[]
            if index==0 and mode!='no_cap':
                outcome='partial_outlet_limit'; used=20000 if mode=='states' else 10
                for _ in range(16):
                    options['on_completed'](baseline); sent.append(baseline)
                    EMITTED.append({'mode':mode,'parent':parent,'synthetic_child':True,'input':data,'candidate':baseline})
                if mode=='time': expired[0]=True
            elif index==1 and mode in ('improve','budget'):
                options['on_completed'](better); sent.append(better); used=3
                EMITTED.append({'mode':mode,'parent':parent,'synthetic_child':True,'input':data,'candidate':better})
                if mode=='budget': outcome='partial_budget'
            elif index==1 and mode=='two_caps':
                outcome='partial_outlet_limit'; used=3
                for _ in range(16):
                    options['on_completed'](baseline); sent.append(baseline)
                    EMITTED.append({'mode':mode,'parent':parent,'synthetic_child':True,'input':data,'candidate':baseline})
            return {'best':better if sent and sent[-1] is better else baseline,
                    'diagnostics':{'kind':'synthetic_dispatch_sentinel','parent':parent,'actual_physical_frontier':False},
                    'stats':{'outcome':outcome,'processed_states':used,'actual_open_count':0,
                             'complete_outputs':len(sent),'synthetic_contract':True}}
        def clock(): return perf_counter()+(1 if expired[0] else 0)
        with patch('isa_scheduler.tree_pair_anytime_refine.schedule_fixed_tree_pair_anytime',child), \
             patch('isa_scheduler.tree_pair_anytime_refine.perf_counter',clock):
            result=refine_fixed_tree_pairs_anytime(data,baseline,time_budget_ms=500,max_states=20000,max_outcomes=16,max_parent_nodes=96)
        RETURNS.append({'mode':mode,'calls':calls,'stats':result['stats'],
                        'diagnostic_sentinels':result['diagnostics'],'best':result['best'],
                        'scope':'Mock child, real selector and actual16 physical sink invocations; not actual pair-family search.'})
        self.assertEqual(len(result['diagnostics']),len(calls))
        return result,calls

    def test_cap_continues_second_improvement_same_initial_and_deadline(self):
        result,calls=self.run_contract('improve')
        self.assertGreaterEqual(len(calls),2); self.assertEqual(calls[1]['remaining_states'],19990)
        self.assertEqual(result['best']['copies'],21); self.assertEqual(result['stats']['complete_outputs'],17)
        self.assertEqual(result['stats']['outcome'],'partial_outlet_limit')
        self.assertEqual(result['stats']['outlet_limited_parents'],[calls[0]['parent']])

    def test_cap_then_budget_preserves_cap_list_and_complete_best(self):
        result,calls=self.run_contract('budget'); self.assertEqual(len(calls),2)
        self.assertEqual(result['stats']['outcome'],'partial_budget'); self.assertEqual(result['best']['copies'],21)
        self.assertEqual(result['stats']['outlet_limited_parents'],[calls[0]['parent']])

    def test_cap_spends_all_states_no_second_child(self):
        result,calls=self.run_contract('states'); self.assertEqual(len(calls),1)
        self.assertEqual(result['stats']['outcome'],'partial_budget')
        self.assertEqual(result['stats']['complete_outputs'],16)
        self.assertEqual(result['stats']['outlet_limited_parents'],[calls[0]['parent']])

    def test_cap_then_deadline_no_second_child(self):
        result,calls=self.run_contract('time'); self.assertEqual(len(calls),1)
        self.assertEqual(result['stats']['outcome'],'partial_budget'); self.assertEqual(result['stats']['complete_outputs'],16)
        self.assertEqual(result['stats']['outlet_limited_parents'],[calls[0]['parent']])

    def test_two_caps_then_exhausted_keeps_overall_partial(self):
        result,calls=self.run_contract('two_caps'); self.assertGreater(len(calls),2)
        self.assertEqual(result['stats']['outcome'],'partial_outlet_limit'); self.assertEqual(result['stats']['complete_outputs'],32)
        self.assertEqual(result['stats']['outlet_limited_parents'],[calls[0]['parent'],calls[1]['parent']])

    def test_without_caps_retains_complete_behavior(self):
        result,calls=self.run_contract('no_cap'); self.assertTrue(calls)
        self.assertEqual(result['stats']['outcome'],'completed'); self.assertEqual(result['stats']['outlet_limited_parents'],[])


if __name__=='__main__': unittest.main()
