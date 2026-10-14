"""CPU-only verifier orchestration checks; does not import torch or use a GPU."""
from dataclasses import dataclass
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from contextlib import redirect_stdout

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('kv_verifier_v24',ROOT/'scripts/verify-kv-policy-v24.py')
v=importlib.util.module_from_spec(spec);sys.modules[spec.name]=v;spec.loader.exec_module(v)

@dataclass
class Generation:
    output:str
    ttft_ms:float
    elapsed_ms:float
    input_tokens:int
    output_tokens:int

class IDs:
    def __init__(self,rows):self.rows=rows
    def detach(self):return self
    def cpu(self):return self
    def tolist(self):return self.rows

class Fake:
    def __init__(self):
        self.events=[];self.device='cuda';self.calls=[]
        self.torch=SimpleNamespace(cuda=SimpleNamespace(
            empty_cache=lambda:self.events.append('empty'),
            memory_allocated=lambda device:20,
            reset_peak_memory_stats=lambda device:self.events.append('reset')))
        self.model=SimpleNamespace(generate=self.generate)
        self.counter=SimpleNamespace(count=len)
    def sync(self):self.events.append('sync')
    def prompt(self,context,task):return context+'\nTASK '+task
    def generate(self,**kwargs):
        tokens=kwargs['input_ids'].rows[0]
        return IDs([tokens+list(range(900,900+kwargs['max_new_tokens']))])


def method(owner,prompt,max_new_tokens):
    ids=[ord(c) for c in prompt]
    owner.calls.append({'policy':owner.kv_cache_policy,'threshold':owner.kv_offload_min_tokens,
                        'chunk':owner.prefill_chunk,'prompt':prompt,'maximum':max_new_tokens})
    output=owner.model.generate(input_ids=IDs([ids]),max_new_tokens=max_new_tokens)
    return Generation('fake output',1.0,2.0,len(ids),len(output.rows[0])-len(ids))

class VerifierTests(unittest.TestCase):
    def test_frozen_inputs_and_source_reference_validated_without_gpu(self):
        folder,baseline,path,reference,expected,probe=v.validate_inputs()
        self.assertEqual(folder,ROOT/'adapters/research-v24')
        self.assertEqual(expected['input_tokens'],32688)
        self.assertEqual(expected['output_tokens'],13)
        self.assertEqual(v.sha(baseline),v.BASELINE_SHA)

    def test_complete_prefix_and_count_enforced(self):
        generation=Generation('',1,2,2,1)
        data=v.token_evidence([[1,2]],[[1,2,3]],generation)
        self.assertEqual(data['output_token_ids'],[[3]])
        self.assertEqual(data['complete_token_ids_sha256'],hashlib.sha256(b'[[1,2,3]]').hexdigest())
        for inputs,complete,g in [([[1,2]],[[9,2,3]],generation),([[1]],[[1,3]],generation),
                                  ([[1,2]],[[1,2,3,4]],generation)]:
            with self.subTest(inputs=inputs,complete=complete),self.assertRaises(AssertionError):
                v.token_evidence(inputs,complete,g)

    def test_short_48_full_ids_all_policies_both_paths_and_two_orders(self):
        model=Fake();capture=v.CompleteCapture(model);report={'short_cases':[]};checkpoints=[]
        with redirect_stdout(io.StringIO()):
            v.verify_short(model,{name:method for name in ['frozen_resident','resident','offloaded','reclaimed']},capture,lambda owner:{'fake':True},report,lambda:checkpoints.append(report.get('short_timed_calls',0)))
        self.assertEqual(report['short_timed_calls'],48)
        self.assertTrue(report['all_short_complete_greedy_ids_equal'])
        self.assertEqual(len(model.calls),48)
        self.assertEqual([c['policy'] for c in model.calls[:8]],['resident','resident','offloaded','reclaimed','reclaimed','offloaded','resident','resident'])
        self.assertEqual({c['chunk'] for c in model.calls},{0,1024})
        self.assertTrue(all(c['threshold']==0 for c in model.calls))
        for case in report['short_cases']:
            self.assertEqual(case['paired_exact_ids_equal'],[True,True])
            for runs in case['runs'].values():
                for run in runs:self.assertEqual(len(run['complete_token_ids'][0]),run['input_tokens']+run['output_tokens'])
        self.assertGreater(len(checkpoints),48)
        self.assertEqual(model.events[:3],['sync','empty','reset'])
        capture.restore()

    def test_failure_pair_saved_with_complete_evidence(self):
        model=Fake();capture=v.CompleteCapture(model);report={'short_cases':[]};snapshots=[]
        def changed(owner,prompt,max_new):
            generation=method(owner,prompt,max_new)
            capture.records[-1][1][0][-1]=42
            return generation
        with redirect_stdout(io.StringIO()),self.assertRaises(AssertionError):
            v.verify_short(model,{'frozen_resident':method,'resident':method,'offloaded':method,'reclaimed':changed},capture,lambda owner:{},report,
                           lambda:snapshots.append(json.loads(json.dumps(report))))
        self.assertEqual(report['short_timed_calls'],4)
        self.assertFalse(report['short_cases'][0]['paired_exact_ids_equal'][0])
        self.assertEqual(len(report['short_cases'][0]['runs']['reclaimed']),1)
        self.assertFalse(snapshots[-1]['short_cases'][0]['paired_exact_ids_equal'][0])

    def test_long_replay_exact_inputs_historical_limit_and_hash(self):
        model=Fake();capture=v.CompleteCapture(model);prompt='x'*32688
        full=[[ord('x')]*32688+list(range(900,913))]
        reference={'maximum_prompt_tokens':32700,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'max_new_tokens':16}
        expected={'complete_token_ids_sha256':v.ids_sha(full)}
        probe=SimpleNamespace(make_prompt=lambda owner,maximum:prompt);report={};saved=[]
        def stopped_at_13(owner,text,maximum):
            # Historical decoding stops naturally after 13 tokens despite its
            # configured 16-token ceiling; retain the requested ceiling in calls.
            original=capture.original
            capture.original=lambda **kw: IDs([kw['input_ids'].rows[0]+list(range(900,913))])
            try:return method(owner,text,maximum)
            finally:capture.original=original
        v.verify_long(model,stopped_at_13,capture,lambda owner:{'fake':True},reference,expected,probe,report,lambda:saved.append(1))
        self.assertEqual(model.calls[-1]['maximum'],16)
        self.assertEqual(report['long_run']['max_new_tokens'],16)
        self.assertEqual(report['long_run']['output_tokens'],13)
        self.assertEqual((model.calls[-1]['policy'],model.calls[-1]['threshold'],model.calls[-1]['chunk']),('reclaimed',16384,1024))
        self.assertTrue(report['long_run']['exact_historical_complete_ids_hash_equal'])
        self.assertEqual(report['long_run']['complete_token_ids'],full)
        self.assertNotIn('in_progress',report)
        self.assertGreaterEqual(len(saved),3)

    def test_long_prompt_failure_before_call_and_existing_output_refused(self):
        model=Fake();capture=v.CompleteCapture(model)
        reference={'maximum_prompt_tokens':32700,'prompt_sha256':'wrong','max_new_tokens':16}
        with self.assertRaises(AssertionError):
            v.verify_long(model,method,capture,lambda owner:{},reference,{'complete_token_ids_sha256':'wrong'},
                          SimpleNamespace(make_prompt=lambda owner,maximum:'x'*32688),{},lambda:None)
        self.assertFalse(model.calls)
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'existing.json';output.write_text('keep')
            with self.assertRaises(FileExistsError):v.main(['--model','fake','--output',str(output)])
            self.assertEqual(output.read_text(),'keep')

if __name__=='__main__':unittest.main(verbosity=2)
