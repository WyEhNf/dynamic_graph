import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'adapters'/'research-v24'))
sys.path.insert(0,str(Path(__file__).parent))
from context_governance.core import Item
from protocol import check_compression, final_answer, search_candidates

class ProtocolTests(unittest.TestCase):
    def test_required_transitive_closure_and_exact_text(self):
        items=[Item('spec','requirement','required',True), Item('target','code','import helper',True),Item('helper','code','x=1'),Item('config','code','limit=3')]
        result={'selected':[vars(x) for x in items]}
        self.assertEqual(check_compression(items,result,{'target':['helper'],'helper':['config']})['status'],'IDENTIFIED_CLOSURE_AND_BYTES_PRESERVED')
        with self.assertRaises(ValueError): check_compression(items,{'selected':result['selected'][:-1]},{'target':['helper'],'helper':['config']})
        changed=[dict(x) for x in result['selected']]
        changed[2]['text']='x=2'
        with self.assertRaises(ValueError): check_compression(items,{'selected':changed},{'target':['helper']})

    def test_invented_ids_and_order_rejected(self):
        items=[Item('a','code','a=1',True),Item('b','code','b=2',True)]
        with self.assertRaises(ValueError): check_compression(items,{'selected':[vars(items[1]),vars(items[0])]},{})
        with self.assertRaises(ValueError): check_compression(items,{'selected':[vars(x) for x in items]+[vars(Item('c','code','c=3'))]},{})

    def test_reasoning_truncation_never_returns_draft_code(self):
        with self.assertRaises(ValueError): final_answer('<think>```python\ndef answer(): return 0\n```')
        self.assertEqual(final_answer('<think>draft</think>final'), 'final')

    def test_public_feedback_only_and_budget_exhaustion(self):
        seen=[]
        def prompt(previous,feedback):
            seen.append((previous,feedback)); return 'public prompt'
        def generate(prompt,index): return {'final_output':str(index)}
        result=search_candidates(generate,lambda x:{'passed':False,'reason':'public failure'},prompt,2)
        self.assertEqual(result.status,'NO_PUBLIC_CHECKED_CANDIDATE')
        self.assertIsNone(result.selected)
        self.assertEqual(seen,[(None,None),('0','public failure')])

    def test_protocol_error_never_executes_candidate(self):
        def verifier(_): self.fail('must not execute a truncated candidate')
        result=search_candidates(lambda p,i:{'final_output':'danger','protocol_error':'truncated'},verifier,lambda p,f:'prompt',1)
        self.assertIsNone(result.selected)

    def test_first_public_pass_returns_explicit_nonproof(self):
        result=search_candidates(lambda p,i:{'final_output':'ok'},lambda x:{'passed':True},lambda p,f:'prompt',2)
        self.assertEqual(result.status,'PUBLIC_CHECKED_NOT_PROVED')
        self.assertEqual(len(result.attempts),1)

if __name__=='__main__': unittest.main()
