"""CPU-only configuration, CLI and fake CUDA/cache lifecycle integration checks.

No GPU/model inference, no measured speed/resource/quality claim. Tensor token
values follow every explicit prefix slice and the final full-input generate.
"""
from contextlib import nullcontext, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0,str(HERE))
from context_governance.local_model import LocalModel, Generation
import context_governance.prepare_model as prepare
import context_governance.run_local_eval as runner
import context_governance.session_metrics as metrics
import context_governance.resources as resources

class Tensor:
    def __init__(self, data): self.data=data
    @property
    def shape(self): return (len(self.data),len(self.data[0]))
    def __getitem__(self,key):
        if isinstance(key,tuple):
            rows,col=key
            if isinstance(rows,int): return self.data[rows][col]
            return Tensor([row[col] for row in self.data[rows]])
        return self.data[key]
    def numel(self): return sum(map(len,self.data))

class Encoded(dict):
    def __getattr__(self,name): return self[name]
    def to(self,device): return self

class Tokenizer:
    eos_token_id=99999
    name_or_path='fake'
    def __call__(self,prompt,return_tensors):
        ids=list(range(len(prompt)))
        return Encoded(input_ids=Tensor([ids]),attention_mask=Tensor([[1]*len(ids)]))
    def decode(self,ids,skip_special_tokens): return ','.join(map(str,ids))
    def apply_chat_template(self,messages,**kw): return json.dumps(messages,ensure_ascii=False)

class Model:
    def __init__(self,events):
        self.events=events; self.config=SimpleNamespace(max_position_embeddings=50000)
        self.chunks=[]; self.generate_kwargs=[]; self.consumed=[]
    def to(self,device): return self
    def eval(self): return self
    def __call__(self,**kw):
        ids=kw['input_ids'].data[0]; cache=kw['past_key_values']
        assert kw['attention_mask'].shape[1]==len(cache.tokens)+len(ids)
        assert kw['use_cache'] and kw['return_dict'] and kw['logits_to_keep']==1
        cache.tokens.extend(ids); self.chunks.append(list(ids)); self.events.append(('prefill',list(ids)))
    def generate(self,**kw):
        self.generate_kwargs.append(kw)
        tokens=kw['input_ids'].data[0]; cache=kw.get('past_key_values')
        prefix=cache.tokens if cache else []
        consumed=prefix+tokens[len(prefix):]
        assert consumed==tokens and len(set(consumed))==len(tokens)
        self.consumed.append(consumed)
        self.events.append(('generate',len(tokens)))
        clock=kw['streamer']; clock.put(Tensor([tokens]))
        generated=[40001+i for i in range(kw['max_new_tokens'])]
        for token in generated: clock.put(Tensor([[token]]))
        clock.end()
        return Tensor([tokens+generated])

class Environment:
    def __init__(self,cuda_available=True):
        self.events=[]; self.caches=[]; self.loads=[]; self.models=[]
        torch=ModuleType('torch'); torch.float16='fp16';torch.float32='fp32'
        torch.set_num_threads=lambda n:None
        torch.device=lambda name:SimpleNamespace(type=name.split(':')[0])
        torch.inference_mode=nullcontext
        torch.cuda=SimpleNamespace(is_available=lambda:cuda_available,
             synchronize=lambda device:self.events.append(('sync',device)),
             empty_cache=lambda:self.events.append(('empty',None)))
        self.torch=torch
        tr=ModuleType('transformers')
        tr.AttentionInterface=SimpleNamespace(register=lambda *args:None)
        def load_tokenizer(*args,**kw):
            self.loads.append('tokenizer');return Tokenizer()
        def load_model(*args,**kw):
            self.loads.append('model'); model=Model(self.events);self.models.append(model);return model
        tr.AutoTokenizer=SimpleNamespace(from_pretrained=load_tokenizer)
        tr.AutoModelForCausalLM=SimpleNamespace(from_pretrained=load_model)
        owner=self
        class Cache:
            def __init__(self,config,offloading=False):
                self.tokens=[]; self.offloading=offloading;owner.caches.append(self)
                owner.events.append(('cache',offloading))
        tr.DynamicCache=Cache
        self.transformers=tr
    def __enter__(self):
        self.stack=patch.dict(sys.modules,{'torch':self.torch,'transformers':self.transformers})
        self.stack.__enter__()
        self.verify=patch.object(prepare,'verify_snapshot',return_value={'repo':'fake'})
        self.verify.__enter__();return self
    def __exit__(self,*args):
        self.verify.__exit__(*args);self.stack.__exit__(*args)
    def owner(self,policy='resident',threshold=10,chunk=4,device='cuda'):
        return LocalModel('fake',device=device,attention='native',prefill_chunk=chunk,
                          kv_cache_policy=policy,kv_offload_min_tokens=threshold)

class PolicyTests(unittest.TestCase):
    def test_configuration_defaults_and_invalid_values(self):
        with Environment(False) as env:
            model=LocalModel('fake',device='cpu',attention='native')
            self.assertEqual((model.kv_cache_policy,model.kv_offload_min_tokens),('resident',16384))
            for policy,threshold in [('bad',0),('resident',-1),('resident',1.5),('resident',True)]:
                with self.subTest(policy=policy,threshold=threshold), self.assertRaises(ValueError):
                    env.owner(policy,threshold,device='cpu')

    def test_cpu_auto_and_explicit_reject_before_loading_model(self):
        for device in ['cpu','cpu:0','auto']:
            for policy in ['offloaded','reclaimed']:
                with self.subTest(device=device,policy=policy), Environment(False) as env:
                    with self.assertRaisesRegex(ValueError,'require CUDA'):
                        env.owner(policy,0,device=device)
                    self.assertEqual(env.loads,[])
        with Environment(True) as env:
            owner=env.owner('offloaded',0,device='cuda:1')
            self.assertEqual(owner.device_type,'cuda')
            self.assertEqual(owner.device,'cuda:1')

    def test_policy_threshold_chunk_matrix_and_complete_tokens(self):
        count=0
        for policy in ['resident','offloaded','reclaimed']:
            for length in [3,4,5,9,10,11,13,17]:
                for chunk in [0,4,7]:
                    for device in (['cpu','cuda'] if policy=='resident' else ['cuda']):
                        with self.subTest(policy=policy,length=length,chunk=chunk,device=device), Environment() as env:
                            owner=env.owner(policy,10,chunk,device)
                            output=owner.generate('x'*length,3)
                            self.assertEqual((output.input_tokens,output.output_tokens),(length,3))
                            self.assertEqual(output.output,'40001,40002,40003')
                            self.assertGreater(output.ttft_ms,0)
                            self.assertEqual(owner.model.consumed,[list(range(length))])
                            eligible=device=='cuda' and policy!='resident' and length>10
                            chunked=bool(chunk and length>chunk)
                            call=owner.model.generate_kwargs[-1]
                            if chunked:
                                self.assertEqual(env.caches[-1].offloading,eligible)
                                self.assertIs(call['past_key_values'],env.caches[-1])
                                self.assertNotIn('cache_implementation',call)
                                self.assertEqual(env.caches[-1].tokens,list(range(length-chunk)))
                                self.assertEqual(sum(map(len,owner.model.chunks)),length-chunk)
                            else:
                                self.assertFalse(env.caches)
                                self.assertEqual(call.get('cache_implementation'), 'offloaded' if eligible else None)
                            empty=[i for i,event in enumerate(env.events) if event[0]=='empty']
                            expected=len(owner.model.chunks) if eligible and policy=='reclaimed' else 0
                            self.assertEqual(len(empty),expected)
                            for index in empty:
                                self.assertEqual(env.events[index-1],('sync',device))
                                self.assertEqual(env.events[index-2][0],'prefill')
                                self.assertLess(index,next(i for i,e in enumerate(env.events) if e[0]=='generate'))
                            count+=1
        self.assertEqual(count,96)

    def test_zero_threshold_and_default_threshold_exact_boundary(self):
        for threshold,length,expected in [(0,5,True),(16384,16384,False),(16384,16385,True)]:
            with self.subTest(threshold=threshold,length=length), Environment() as env:
                owner=env.owner('reclaimed',threshold,2 if length<4096 else 4096)
                owner.generate('x'*length,2)
                self.assertEqual(env.caches[-1].offloading,expected)
                self.assertEqual(any(e[0]=='empty' for e in env.events),expected)

    def test_resident_legacy_new_owner_and_consecutive_cache_isolation(self):
        with Environment() as env:
            owner=env.owner('resident',0,4)
            del owner.kv_cache_policy;del owner.kv_offload_min_tokens
            first=owner.generate('x'*13,2); second=owner.generate('x'*17,2)
            self.assertEqual(first.output,second.output)
            self.assertEqual(len(env.caches),2)
            self.assertIsNot(env.caches[0],env.caches[1])
            self.assertEqual(env.caches[0].tokens,list(range(9)))
            self.assertEqual(env.caches[1].tokens,list(range(13)))
            self.assertFalse(any(e[0]=='empty' for e in env.events))

    def test_context_overflow_before_cache_and_decode(self):
        with Environment() as env:
            owner=env.owner('reclaimed',0,4);owner.model.config.max_position_embeddings=16
            with self.assertRaisesRegex(ValueError,'exceeds model context'):
                owner.generate('x'*15,2)
            self.assertFalse(env.caches)
            self.assertFalse(owner.model.generate_kwargs)
            self.assertFalse(any(e[0]=='empty' for e in env.events))

    def test_complete_baseline_sha_other_modules_and_prompt_protocols(self):
        record=json.loads((HERE/'provenance.json').read_text())
        self.assertEqual(len(record['baseline_source_sha256']),25)
        self.assertEqual(record['changed_modules'],['local_model.py','public_examples.py','run_local_eval.py'])
        for name,expected in record['baseline_source_sha256'].items():
            self.assertEqual(hashlib.sha256((HERE/'baseline-source'/name).read_bytes()).hexdigest(),expected)
            self.assertEqual(hashlib.sha256((HERE.parent/'research-v22/context_governance'/name).read_bytes()).hexdigest(),expected)
            if name not in record['changed_modules']:
                self.assertEqual((HERE/'context_governance'/name).read_bytes(),(HERE/'baseline-source'/name).read_bytes())
        spec=importlib.util.spec_from_file_location('context_governance._baseline_v22',HERE/'baseline-source/local_model.py')
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        owner=SimpleNamespace(tokenizer=Tokenizer(),prompt_policy='concise-v3')
        for context,task,target in [('ctx','Implement double(x).','# placeholder'),('def helper(x): return x','Implement scale(x).','def legacy(x): return x')]:
            for protocol in ['literal-v17','public-contract-v22']:
                self.assertEqual(LocalModel.examples_prompt(owner,context,task,target,protocol),
                                 module.LocalModel.examples_prompt(owner,context,task,target,protocol))
            self.assertEqual(LocalModel.prompt(owner,context,task),module.LocalModel.prompt(owner,context,task))
            self.assertEqual(LocalModel.review_prompt(owner,context,task,'draft'),module.LocalModel.review_prompt(owner,context,task,'draft'))

    def test_generator_reproduces_all_25_candidate_files(self):
        with tempfile.TemporaryDirectory() as folder:
            import shutil,subprocess
            root=Path(folder);v24=root/'research-v24';v24.mkdir()
            shutil.copytree(HERE/'baseline-source',root/'research-v22/context_governance')
            reference=root/'sdpa/research-v23';reference.mkdir(parents=True)
            shutil.copyfile(HERE.parent/'sdpa/research-v23/local_model.py',reference/'local_model.py')
            shutil.copyfile(HERE/'generate_candidate.py',v24/'generate_candidate.py')
            subprocess.run([sys.executable,'-B',str(v24/'generate_candidate.py')],check=True,capture_output=True)
            for p in (HERE/'context_governance').glob('*.py'):
                self.assertEqual(p.read_bytes(),(v24/'context_governance'/p.name).read_bytes(),p.name)

    def test_public_examples_reject_keyword_module_paths(self):
        from context_governance.public_examples import evaluate_examples
        response=json.dumps([{'function':'double','args_python':'[3]','expected_python':'6'}])
        for target in ['class.py','pkg/while.py','for/solution.py']:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);source=root/target;source.parent.mkdir(parents=True,exist_ok=True)
                source.write_text('def double(x): return x * 2',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'module path is not importable'):
                    evaluate_examples(response,'def double(x): return x * 2',root,target,
                                      checker=lambda *a: self.fail('invalid module path must reject before checker'),
                                      public_task='Implement double(x).')

    def test_cli_validation_before_suite_loading(self):
        for arguments in [['--kv-cache-policy','unknown'],['--kv-offload-min-tokens','-1']]:
            with patch.object(sys,'argv',['evaluation','--model','fake',*arguments]), patch.object(runner,'load_case') as load:
                with redirect_stdout(io.StringIO()), patch('sys.stderr',io.StringIO()), self.assertRaises(SystemExit):
                    runner.main()
                load.assert_not_called()

    def test_cli_default_single_and_explicit_report_fields(self):
        class Ledger:
            def __init__(self,*args):pass
            def record_pair(self,*args,**kw):pass
            def summary(self,*args):return {'fake':True}
        for policy,threshold,options in [('resident',16384,[]),('reclaimed',0,['--kv-cache-policy','reclaimed','--kv-offload-min-tokens','0'])]:
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as folder, Environment() as env:
                root=Path(folder); (root/'tests').mkdir();(root/'oracle').mkdir();(root/'solution.py').write_text('# placeholder')
                (root/'manifest.json').write_text(json.dumps({'case_ids':['fake'],'version':'mock'}))
                (root/'tests/fake.py').write_text('# fake');(root/'oracle/fake.py').write_text('def f():pass')
                output=root/'report.json'
                metadata={'target_file':'solution.py','context_dependencies':{},'snapshot_sha256':'mock'}
                governed={'context':'compressed','metrics':{'governance_ms':0.1,'importance_analysis_ms':0.1}}
                args=['eval','--model','fake','--device','cuda','--attention','native','--repeats','1','--suite',str(root),'--output',str(output),'--metrics-db',str(root/'m.db'),*options]
                with patch.object(sys,'argv',args), patch.object(runner,'load_case',return_value=(metadata,root,'Implement f().',[])), patch.object(runner,'render',return_value='baseline'), patch.object(runner,'govern',return_value=governed),patch.object(runner,'check_code',return_value={'passed':True}), patch.object(metrics,'SessionMetrics',Ledger),patch.object(resources,'resource_snapshot',return_value={'fake':True}), redirect_stdout(io.StringIO()):
                    env.torch.__version__='fake'
                    runner.main()
                report=json.loads(output.read_text())
                self.assertEqual(report['kv_cache_policy'],policy)
                self.assertEqual(report['kv_offload_min_tokens'],threshold)
                self.assertFalse(report['self_review'])
                self.assertIsNone(report['public_examples_protocol'])
                self.assertEqual(report['summary']['model_generation_calls'],2)
                self.assertEqual(len(env.models[0].generate_kwargs),5) # 3 warmups + 2 single calls
                if policy=='reclaimed':
                    self.assertTrue(all(c.get('cache_implementation')=='offloaded' for c in env.models[0].generate_kwargs))
                else:
                    self.assertTrue(all('cache_implementation' not in c for c in env.models[0].generate_kwargs))

if __name__=='__main__':
    destination=HERE/'test-results.json'
    if destination.exists():raise FileExistsError(destination)
    started=time.perf_counter()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record={'tests_run':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'successful':result.wasSuccessful(),
            'wall_seconds':time.perf_counter()-started,'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'Fake GPU/cache and CPU configuration only; no GPU inference, timings, memory savings or model-quality evidence.'}
    destination.write_text(json.dumps(record,indent=2)+'\n')
    if not result.wasSuccessful():raise SystemExit(1)
