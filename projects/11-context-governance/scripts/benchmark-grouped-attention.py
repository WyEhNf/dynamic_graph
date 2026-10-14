"""Independent small math oracle and checkpointed paired GPU allocator milestone.

No models are loaded. This v19b microbenchmark forces grouped dispatch and does
not establish model quality, real-policy benefit, or an independent speedup.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
BASELINE_SHA='4b33707a68a1ce1f3e28e3ee84ea27bda9cbfc9f3d44abe82bc245faa16a68c6'
CANDIDATE_SHA='3b552ebee14a23db969a1eacf3bfb3725a148a450d0a1e10567291d56e5f6f4a'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(ROOT/'artifacts/grouped-attention-v19.json'))
    args=parser.parse_args(argv)
    output=Path(args.output).resolve()
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    paths={'baseline':ROOT/'adapters/research-v17d-source/local_model.py',
           'candidate':ROOT/'adapters/sdpa/research-v19b/local_model.py'}
    started=time.time();torch=None
    report={'status':'initializing','started_unix':started,'invocation':[sys.executable,*sys.argv],
            'source_paths':{name:str(path) for name,path in paths.items()},
            'expected_source_sha256':{'baseline':BASELINE_SHA,'candidate':CANDIDATE_SHA},
            'script_sha256':sha(__file__),'cpu_math_checks':[],'gpu_pairs':[],
            'predeclared_cpu_math_checks':6,'predeclared_gpu_shapes':18,'paired_rounds_per_gpu_shape':5,
            'predeclared_timed_sdpa_calls':180,'model_loads':0,'seed':1901,'cpu_threads':4,
            'predeclared_head_configurations':[[14,2],[16,2],[28,4]],
            'predeclared_gpu_token_shapes':[[1,4096],[1,32700],[256,16380],[256,32700],[1024,16380],[1024,32700]],
            'forced_grouping_min_kv_tokens':0,'real_candidate_grouping_min_kv_tokens':16384,
            'scope':'Inference microbenchmark only; no model calls or weights loaded. Force grouped dispatch with threshold0; frozen v19b real policy only groups above 16384 KV tokens. Six small float32 CPU cases against an independent float64 dense-softmax oracle, including top-left causal masks and genuinely varying per-query-head masks. Eighteen GPU shapes (the original fifteen plus q1/K32700 for each head configuration) use explicit suffix-aligned causal masks (or no mask for decode), is_causal=False, five alternating paired rounds. Long-window decode is included because real-policy grouping above 16384 KV tokens can add serial/head-group dispatch cost during decode; long-prefill observations must be considered with decode costs. All negative latencies retained; no engineering quality score or model-performance inference.',
            'measurement_scope':'GPU synchronized host wall time includes Python dispatch and attention/contiguous-output work, excludes CPU output transfer and JSON checkpoint IO. Allocation baseline measured after warmup/sync, before each call; incremental live allocator peak=absolute max_memory_allocated minus memory_allocated before call, including output and tracked workspace. Reserved block peaks are separately recorded and may reflect warmed reusable blocks. CPU comparison outputs live only on host. CUDA allocator excludes non-PyTorch/whole-device memory; host process peak is not measured here.'}
    def save():output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    save() # Preserve intent/source paths before dependency import or CUDA initialization.
    try:
        report['source_sha256']={name:sha(path) for name,path in paths.items()};save()
        if report['source_sha256']!=report['expected_source_sha256']:
            raise ValueError('frozen baseline or v19b candidate source differs')
        sys.dont_write_bytecode=True
        baseline=load_module('_frozen_grouped_attention_baseline_v17d',paths['baseline']).expanded_kv_sdpa
        candidate=load_module('_frozen_grouped_attention_candidate_v19b',paths['candidate']).expanded_kv_sdpa
        import torch
        owner=SimpleNamespace(is_causal=True,_context_head_group_min_tokens=0)
        report.update(torch_version=torch.__version__,cuda_runtime_version=torch.version.cuda,
                      flash_attention_available_in_build=torch.backends.cuda.is_flash_attention_available(),
                      cpu_default_dtype=str(torch.get_default_dtype()))
        torch.manual_seed(1901);torch.set_num_threads(4)
        report['status']='cpu_math_checks';save()
        with torch.inference_mode():
            for heads,kv in [(14,2),(16,2),(28,4)]:
                for causal in [True,False]:
                    report['in_progress']={'stage':'cpu','query_heads':heads,'kv_heads':kv,'causal':causal};save()
                    q=torch.randn(1,heads,8,128,dtype=torch.float32)
                    k=torch.randn(1,kv,37,128,dtype=torch.float32);v=torch.randn_like(k)
                    mask=None
                    if not causal:
                        mask=torch.zeros(1,heads,8,37,dtype=torch.float32)
                        # Vary the blocked key set by query head so a candidate
                        # using another KV group's mask cannot pass accidentally.
                        for head in range(heads):mask[:,head,:,head%3::3]=-float('inf')
                    keys=k.double().repeat_interleave(heads//kv,dim=1)
                    values=v.double().repeat_interleave(heads//kv,dim=1)
                    scores=q.double()@keys.transpose(-1,-2)/math.sqrt(128)
                    if causal:
                        scores=scores.masked_fill(torch.arange(37)[None,:]>torch.arange(8)[:,None],-float('inf'))
                    else:scores=scores+mask.double()
                    reference=(torch.softmax(scores,dim=-1)@values).transpose(1,2).float()
                    out,_=candidate(owner,q,k,v,mask,is_causal=causal)
                    error=(out-reference).abs().max().item()
                    torch.testing.assert_close(out,reference,atol=2e-6,rtol=2e-5)
                    report['cpu_math_checks'].append({'query_heads':heads,'kv_heads':kv,'query_tokens':8,'key_tokens':37,
                        'causal':causal,'mask_kind':'top-left causal' if causal else 'varying per-query-head additive',
                        'max_absolute_error':error,'oracle':'float64 QK/sqrt(128), explicit mask, softmax, V; independent of SDPA',
                        'atol':2e-6,'rtol':2e-5,'passed':True})
                    report.pop('in_progress',None);save()
                    del q,k,v,mask,keys,values,scores,reference,out
            if not torch.cuda.is_available():raise RuntimeError('GPU paired milestone requires CUDA; completed CPU records retained')
            report.update(status='gpu_pairs',gpu_device=torch.cuda.get_device_name(),gpu_capability=list(torch.cuda.get_device_capability()),
                          gpu_dtype='float16',allow_tf32_matmul=torch.backends.cuda.matmul.allow_tf32)
            save()
            methods={'expanded':baseline,'grouped':candidate}
            for heads,kv in [(14,2),(16,2),(28,4)]:
                for query_len,key_len in [(1,4096),(1,32700),(256,16380),(256,32700),(1024,16380),(1024,32700)]:
                    record={'query_heads':heads,'kv_heads':kv,'query_tokens':query_len,'key_tokens':key_len,
                            'mask_head_dimension':None if query_len==1 else 1,
                            'mask_kind':'none, single decode query sees all cached keys' if query_len==1 else 'suffix-aligned causal additive, key<=query+K-Q',
                            'sdpa_is_causal':False,'real_candidate_would_group':key_len>16384,'samples':{name:[] for name in methods},'comparison_rounds':[],'status':'allocating'}
                    report['gpu_pairs'].append(record)
                    report['in_progress']={'stage':'gpu_shape','query_heads':heads,'kv_heads':kv,'query_tokens':query_len,'key_tokens':key_len,'phase':'allocating'};save()
                    q=torch.randn(1,heads,query_len,128,device='cuda',dtype=torch.float16)
                    k=torch.randn(1,kv,key_len,128,device='cuda',dtype=torch.float16);v=torch.randn_like(k)
                    mask=None
                    if query_len>1:
                        allowed=torch.arange(key_len,device='cuda')[None,:] <= (torch.arange(query_len,device='cuda')+key_len-query_len)[:,None]
                        mask=torch.zeros(query_len,key_len,device='cuda',dtype=torch.float16).masked_fill(~allowed,-float('inf'))[None,None]
                        del allowed
                    record['status']='warming';report['in_progress']['phase']='warming';save()
                    for function in methods.values():
                        warm,_=function(owner,q,k,v,mask,is_causal=False);del warm
                    torch.cuda.synchronize()
                    record['status']='paired_rounds';maximum_error=0.0
                    for repeat in range(5):
                        outputs={}
                        for name in (['expanded','grouped'] if repeat%2==0 else ['grouped','expanded']):
                            report['in_progress'].update(phase='timed_call',method=name,repeat=repeat);save()
                            torch.cuda.synchronize()
                            before=torch.cuda.memory_allocated();reserved_before=torch.cuda.memory_reserved()
                            torch.cuda.reset_peak_memory_stats()
                            tick=time.perf_counter_ns()
                            out,_=methods[name](owner,q,k,v,mask,is_causal=False)
                            torch.cuda.synchronize();elapsed=(time.perf_counter_ns()-tick)/1e6
                            peak=torch.cuda.max_memory_allocated();reserved_peak=torch.cuda.max_memory_reserved()
                            outputs[name]=out.cpu();del out
                            record['samples'][name].append({'repeat':repeat,'order':0 if len(outputs)==1 else 1,
                                'wall_ms':elapsed,'resident_allocator_bytes_before':before,'absolute_peak_allocator_bytes':peak,
                                'incremental_peak_allocator_bytes':peak-before,'reserved_allocator_bytes_before':reserved_before,
                                'absolute_peak_reserved_allocator_bytes':reserved_peak,'incremental_reserved_bytes':reserved_peak-reserved_before})
                            save()
                        error=(outputs['expanded']-outputs['grouped']).abs().max().item();maximum_error=max(maximum_error,error)
                        comparison={'repeat':repeat,'max_absolute_difference':error,'atol':0.003,'rtol':0.001,'passed':False}
                        record['comparison_rounds'].append(comparison);save()
                        torch.testing.assert_close(outputs['expanded'],outputs['grouped'],atol=0.003,rtol=0.001)
                        comparison['passed']=True;save()
                    record.update(status='complete',maximum_absolute_difference=maximum_error,
                        wall_median_ms={name:statistics.median(x['wall_ms'] for x in rows) for name,rows in record['samples'].items()},
                        incremental_peak_bytes={name:max(x['incremental_peak_allocator_bytes'] for x in rows) for name,rows in record['samples'].items()})
                    report.pop('in_progress',None);save()
                    print(json.dumps({k:record[k] for k in ['query_heads','query_tokens','key_tokens','wall_median_ms','incremental_peak_bytes','maximum_absolute_difference']}),flush=True)
                    del q,k,v,mask,outputs
                    torch.cuda.empty_cache()
        if len(report['cpu_math_checks'])!=6 or len(report['gpu_pairs'])!=18 or any(r['status']!='complete' for r in report['gpu_pairs']):
            raise AssertionError('predeclared batch did not complete')
        if {name:sha(path) for name,path in paths.items()}!=report['expected_source_sha256']:
            raise ValueError('frozen source changed during execution')
        report.update(status='complete',finished_unix=time.time())
        report['wall_seconds']=report['finished_unix']-started;save()
        print(json.dumps({'cpu_math_checks':6,'gpu_shapes':18,'timed_sdpa_calls':180,'wall_seconds':report['wall_seconds']}))
    except BaseException as error:
        report.update(status='failed',exception_type=type(error).__name__,error=str(error),finished_unix=time.time())
        report['wall_seconds']=report['finished_unix']-started
        if torch is not None:
            try:
                if torch.cuda.is_initialized():
                    report['cuda_allocator_at_failure']={'allocated_bytes':torch.cuda.memory_allocated(),
                        'reserved_bytes':torch.cuda.memory_reserved(),'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
                        'peak_reserved_bytes':torch.cuda.max_memory_reserved()}
            except Exception as diagnostic_error:report['diagnostic_error']=str(diagnostic_error)
        save();raise

if __name__=='__main__':main()
