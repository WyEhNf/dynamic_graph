"""Opt-in v24 API integration verification, one CUDA model load; no quality score.

Parent must explicitly run this in its model environment. Importing this file
performs no model import, GPU initialization or generation. Short verification
uses 48 calls; long verification replays one historical v23 prompt, not a new
independent speedup experiment. Sources and full token arrays are retained.
"""
import argparse
from dataclasses import asdict
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
FROZEN_SHA='9548ba0d5c8c1a3c7bb11ddf0c216b132b6990078b430d4636fd54cf50e2f5c2'
BASELINE_SHA='4b33707a68a1ce1f3e28e3ee84ea27bda9cbfc9f3d44abe82bc245faa16a68c6'
EXPECTED_LONG_PROMPT_SHA='9fa6e0d594c23781da49d7a8bc1941b2c5c4d2af3f06ca73b55c7b9084b6b8b2'
EXPECTED_LONG_IDS_SHA='a0c10e8909fbca3761c419fab2ad025d12d55a8d17dc9a64b3d18000c07933a0'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ids_sha(ids):return hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def validate_inputs(root=ROOT):
    folder=root/'adapters/research-v24'
    manifest_path=folder/'freeze-manifest.json'
    if sha(manifest_path)!=FROZEN_SHA:raise ValueError('v24 freeze manifest differs')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for name,expected in manifest['file_sha256'].items():
        if sha(folder/name)!=expected:raise ValueError('v24 frozen file differs: '+name)
    baseline=root/'adapters/research-v17d-source/local_model.py'
    if sha(baseline)!=BASELINE_SHA:raise ValueError('frozen v17d resident source differs')
    reference_path=root/'artifacts/long-kv-token-compatibility-v23.json'
    reference=json.loads(reference_path.read_text(encoding='utf-8'))
    if reference['max_new_tokens']!=16:raise ValueError('historical generation ceiling differs')
    if not reference.get('exact_complete_greedy_ids_equal'):raise ValueError('v23 reference was not compatible')
    if reference['prompt_sha256']!=EXPECTED_LONG_PROMPT_SHA:raise ValueError('unexpected historical long prompt')
    runs=[r for r in reference['runs'] if r['method']=='reclaimed']
    if len(runs)!=1:raise ValueError('expected exactly one historical v23 reclaimed record')
    expected=runs[0]
    if (expected['input_tokens'],expected['output_tokens'])!=(32688,13):raise ValueError('historical token counts differ')
    if expected['complete_token_ids_sha256']!=EXPECTED_LONG_IDS_SHA:raise ValueError('historical complete IDs differ')
    probe=root/'scripts/probe-model-capacity.py'
    if sha(probe)!=reference['prompt_generator_sha256']:raise ValueError('historical prompt generator differs')
    source_reference=root/'adapters/sdpa/research-v23/local_model.py'
    if sha(source_reference)!=reference['source_sha256']['reclaimed']:raise ValueError('historical v23 source differs')
    return folder,baseline,reference_path,reference,expected,probe


class CompleteCapture:
    """Same CPU capture overhead for each method; retains prompt prefix and IDs."""
    def __init__(self,model):
        self.records=[];self.model=model;self.original=model.model.generate
        def capture(*args,**kwargs):
            inputs=kwargs['input_ids'].detach().cpu().tolist()
            output=self.original(*args,**kwargs)
            self.records.append((inputs,output.detach().cpu().tolist()))
            return output
        model.model.generate=capture
    def take(self):
        if len(self.records)!=1:raise ValueError('expected exactly one complete-ID capture')
        return self.records.pop()
    def clear(self):self.records.clear()
    def restore(self):self.model.model.generate=self.original


def token_evidence(input_ids,complete_ids,generation):
    if len(input_ids)!=1 or len(complete_ids)!=1:raise ValueError('batch must contain exactly one prompt')
    count=len(input_ids[0])
    if complete_ids[0][:count]!=input_ids[0]:raise AssertionError('complete output lost or changed the prompt prefix')
    output_ids=[complete_ids[0][count:]]
    if count!=generation.input_tokens or len(output_ids[0])!=generation.output_tokens:
        raise AssertionError('generation token counters disagree with complete arrays')
    return {'input_token_ids':input_ids,'output_token_ids':output_ids,'complete_token_ids':complete_ids,
            'input_token_ids_sha256':ids_sha(input_ids),'output_token_ids_sha256':ids_sha(output_ids),
            'complete_token_ids_sha256':ids_sha(complete_ids)}


def call_record(model,method,capture,prompt,max_new_tokens,resource_snapshot,*,policy,threshold,chunk):
    model.kv_cache_policy=policy;model.kv_offload_min_tokens=threshold;model.prefill_chunk=chunk
    capture.clear();gc.collect();model.sync();model.torch.cuda.empty_cache()
    resident=model.torch.cuda.memory_allocated(model.device)
    model.torch.cuda.reset_peak_memory_stats(model.device)
    started=time.perf_counter()
    generation=method(model,prompt,max_new_tokens)
    wall=time.perf_counter()-started
    inputs,ids=capture.take()
    resources=resource_snapshot(model)
    evidence=token_evidence(inputs,ids,generation)
    return {**asdict(generation),**evidence,'call_wall_seconds':wall,
            'policy':policy,'kv_offload_min_tokens':threshold,'prefill_chunk_tokens':chunk,
            'resident_cuda_bytes_before':resident,'resources':resources}


def verify_short(model,methods,capture,resource_snapshot,report,save):
    tasks=['Return def identity(x): return x.', 'Return def twice(x): return x * 2.',
           'Return def sorted_unique(xs): return sorted unique values from xs, without changing xs.']
    timed=0
    # Six prompts x two alternating rounds x frozen baseline + three v24 policies.
    for count,chunk in [(64,0),(256,1024)]:
        context=''.join(f'def unused_{i}(x): return x + {i}\n' for i in range(count))
        for task in tasks:
            prompt=model.prompt(context,task)
            record={'unrelated_functions':count,'public_task':task,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                    'prefill_chunk_tokens':chunk,'runs':{name:[] for name in methods},'paired_exact_ids_equal':[],'exact_ids_equal_to_frozen':[]}
            report['short_cases'].append(record)
            for repeat in range(2):
                for name in (list(methods) if repeat%2==0 else list(reversed(methods))):
                    report['in_progress']={'stage':'short','method':name,'count':count,'repeat':repeat,'started_unix':time.time()};save()
                    item=call_record(model,methods[name],capture,prompt,96,resource_snapshot,
                                     policy='resident' if name=='frozen_resident' else name,threshold=0,chunk=chunk)
                    item.update(repeat=repeat,method=name)
                    if chunk and item['input_tokens']<=chunk:raise AssertionError('predeclared chunked case did not enter chunked path')
                    record['runs'][name].append(item);timed+=1
                    report['short_timed_calls']=timed;report.pop('in_progress',None);save()
                baseline_ids=record['runs']['frozen_resident'][repeat]['complete_token_ids']
                comparisons={name:record['runs'][name][repeat]['complete_token_ids']==baseline_ids
                             for name in methods if name!='frozen_resident'}
                equal=all(comparisons.values())
                record['exact_ids_equal_to_frozen'].append(comparisons)
                record['paired_exact_ids_equal'].append(equal);save()
                if not equal:raise AssertionError('v24 policy changed complete greedy IDs; failed pair retained')
            print(json.dumps({'short_count':count,'prefill_chunk':chunk,'all_pairs_equal':True}),flush=True)
    if timed!=48:raise AssertionError('short verification requires exactly 48 calls')
    report['all_short_complete_greedy_ids_equal']=True;save()


def verify_long(model,method,capture,resource_snapshot,reference,expected,probe,report,save):
    prompt=probe.make_prompt(model,reference['maximum_prompt_tokens'])
    prompt_sha=hashlib.sha256(prompt.encode()).hexdigest()
    count=model.counter.count(prompt)
    report['long_input']={'prompt_sha256':prompt_sha,'token_counter_count':count,
                          'historical_prompt_sha256':reference['prompt_sha256'],'historical_input_tokens':32688,
                          'expected_output_tokens':13,'historical_complete_token_ids_sha256':expected['complete_token_ids_sha256']}
    save()
    if prompt_sha!=reference['prompt_sha256'] or count!=32688:raise AssertionError('long prompt differs before generation')
    report['in_progress']={'stage':'long','method':'reclaimed','started_unix':time.time()};save()
    # Preserve the historical max_new_tokens=16 configuration and require its
    # actual 13-token output, including the unchanged full-sequence hash.
    item=call_record(model,method,capture,prompt,reference['max_new_tokens'],resource_snapshot,policy='reclaimed',threshold=16384,chunk=1024)
    item.update(method='reclaimed',max_new_tokens=reference['max_new_tokens'],historical_max_new_tokens=reference['max_new_tokens'],
                exact_historical_complete_ids_hash_equal=item['complete_token_ids_sha256']==expected['complete_token_ids_sha256'],
                prompt_sha256=prompt_sha)
    report['long_run']=item;report.pop('in_progress',None);save()
    if (item['input_tokens'],item['output_tokens'])!=(32688,13) or not item['exact_historical_complete_ids_hash_equal']:
        raise AssertionError('long v24 API integration differs from historical v23 complete IDs; evidence retained')


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--output',default=str(ROOT/'artifacts/kv-policy-api-compatibility-v24.json'))
    args=parser.parse_args(argv)
    output=Path(args.output).resolve()
    if output.exists():raise FileExistsError(output)
    folder,baseline_path,reference_path,reference,expected,probe_path=validate_inputs()
    # The isolated package provides unchanged model verification/resource helpers;
    # no active src imports or frozen-file bytecode writes are permitted.
    sys.dont_write_bytecode=True;sys.path.insert(0,str(folder))
    from context_governance.local_model import LocalModel
    from context_governance.prepare_model import verify_snapshot
    from context_governance.resources import resource_snapshot
    actual=Path(sys.modules[LocalModel.__module__].__file__).resolve()
    if actual!=folder/'context_governance/local_model.py':raise ValueError('wrong package imported; start a fresh process')
    baseline=load_module('context_governance._resident_v17d',baseline_path)
    probe=load_module('_capacity_prompt_v24_verifier',probe_path)
    started=time.time();model=None;capture=None
    report={'origin':'v24 optional API integration; no independent performance improvement or quality score',
            'status':'model_loading_and_warmup','started_unix':started,'invocation':[sys.executable,*sys.argv],
            'script_sha256':sha(__file__),'v24_freeze_manifest_sha256':sha(folder/'freeze-manifest.json'),
            'source_sha256_at_start':{p.name:sha(p) for p in (folder/'context_governance').glob('*.py')},
            'baseline_v17d_source_sha256':sha(baseline_path),'reference_report_sha256':sha(reference_path),
            'prompt_generator_sha256':sha(probe_path),'short_timed_calls':0,'short_cases':[],
            'predeclared_model_loads':1,'predeclared_short_calls':48,'predeclared_long_calls':1,'warmup_generation_calls':4,
            'scope':'One model load; same NF4 weights, expanded SDPA, greedy decoding. Short: frozen v17d resident method versus v24 resident/offloaded/reclaimed APIs threshold0; three nonchunked and three chunked prompts, two alternating rounds. Long: one 32688-input replay with historical max_new_tokens=16 and expected actual output13 against the previous v23 prompt/full-ID SHA, not another independent speedup experiment. Full input/output arrays are stored. Both generation timings include a common CPU token-ID capture wrapper; explicit pre-call GC/sync/empty_cache/peak reset excluded. Process RAM peak cumulative; per-call CUDA allocator peak only, not whole-device usage. No engineering quality oracle.'}
    def save():
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    try:
        model=LocalModel(args.model,'cuda',attention='expanded',prefill_chunk=1024,quantization='nf4',
                         kv_cache_policy='reclaimed',kv_offload_min_tokens=0)
        if model.manifest['repo']!=reference['model_manifest']['repo'] or model.manifest['files']!=reference['model_manifest']['files']:
            raise ValueError('model snapshot differs from historical v23 reference')
        report.update(model_manifest=model.manifest,torch_version=model.torch.__version__,
                      model_loads=1,device=model.device,attention=model.attention,weight_quantization=model.quantization)
        methods={'frozen_resident':baseline.LocalModel.generate,'resident':LocalModel.generate,
                 'offloaded':LocalModel.generate,'reclaimed':LocalModel.generate}
        capture=CompleteCapture(model)
        warm=model.prompt('Warmup.','Return def identity(x): return x.')
        for name,method in methods.items():
            model.kv_cache_policy='resident' if name=='frozen_resident' else name
            model.kv_offload_min_tokens=0;model.prefill_chunk=0
            method(model,warm,16)
        capture.clear();report['status']='short_compatibility';save()
        verify_short(model,methods,capture,resource_snapshot,report,save)
        report['status']='long_api_integration';save()
        verify_long(model,LocalModel.generate,capture,resource_snapshot,reference,expected,probe,report,save)
        final_manifest=verify_snapshot(args.model)
        if final_manifest['files']!=model.manifest['files']:raise ValueError('model files changed during verification')
        validate_inputs()
        report.update(model_files_verified_at_finalization=True,status='complete',finished_unix=time.time())
        report['wall_seconds']=report['finished_unix']-started;save()
        print(json.dumps({'short_calls':48,'long_calls':1,'complete_short_ids_equal':True,
                          'historical_long_hash_equal':True,'output':str(output)}),flush=True)
    except BaseException as error:
        report.update(status='failed',exception_type=type(error).__name__,error=str(error),finished_unix=time.time())
        report['wall_seconds']=report['finished_unix']-started
        if model is not None:
            try:report['resources_at_failure']=resource_snapshot(model)
            except Exception as resource_error:report['resource_error']=str(resource_error)
        save();raise
    finally:
        if capture is not None:capture.restore()

if __name__=='__main__':main()
