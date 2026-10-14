"""Milestone before/after CPU governance and CUDA attention evaluation."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
from .core import govern, Item
from .local_model import ModelTokenCounter, LocalModel, expanded_kv_sdpa
from .bundles import load_case


def legacy_govern(path):
    spec=importlib.util.spec_from_file_location('research_baseline_core',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module.govern


def main():
    from transformers import AutoTokenizer
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--suite',default='fixtures/research-v3')
    parser.add_argument('--output',default='artifacts/research-governance.json')
    parser.add_argument('--attention-check',action='store_true')
    args=parser.parse_args()
    tokenizer=AutoTokenizer.from_pretrained(args.model,local_files_only=True,trust_remote_code=False)
    counter=ModelTokenCounter(tokenizer)
    baseline=legacy_govern(Path('artifacts/research-baseline/core.py'))
    rows=[]
    ids=json.loads((Path(args.suite)/'manifest.json').read_text())['case_ids']
    workloads=[]
    for case_id in ids:
        metadata,_,task,items=load_case(Path(args.suite),case_id)
        workloads.append((case_id,task,items,metadata['context_dependencies']))
    # Genuine distribution changes: many shared lexical distractors, relevant
    # errors, atomic dependency groups, pins and mixtures of English/Chinese.
    for count in [64,256,1024]:
        items=[Item('constraints','requirement','Fix parser handling of invalid integers. 保留错误信息。',True)]
        items.extend(Item(f'module-{i}','code',f'def parser_variant_{i}(value):\n    return value + {i}\n'+'# legacy detail 中文说明\n'*8) for i in range(count))
        items += [Item('latest-error','tool','ERROR parser: invalid integer',True)]
        dependencies={f'module-{i}':[f'module-{i-1}'] for i in range(1,count,13)}
        workloads.append((f'wide-{count}','Fix parser invalid integers',items,dependencies))
    for case_id,task,items,deps in workloads:
        results={}; samples={}
        for mode,operation in [('before',baseline),('after',govern),
                               ('after_request',lambda task,items,budget,counter,deps: govern(task,items,budget,counter,deps,measure_input=False))]:
            operation(task,items,650,counter,deps)
            samples[mode]=[]
            for _ in range(7):
                start=time.perf_counter_ns(); result=operation(task,items,650,counter,deps)
                samples[mode].append((time.perf_counter_ns()-start)/1e6)
            if result['metrics']['output_units']>650: raise RuntimeError('budget violation')
            selected={x['id'] for x in result['selected']}
            if not all(set(deps.get(x,[]))<=selected for x in selected): raise RuntimeError('dependency violation')
            results[mode]={'output_tokens':result['metrics']['output_units'],'selected_items':len(selected),
                           'median_ms':statistics.median(samples[mode]),'samples_ms':samples[mode],
                           'importance_ms':result['metrics']['importance_analysis_ms']}
        row={'id':case_id,'input_tokens':counter.count('\n\n'.join(f'[{x.kind}:{x.id}]\n{x.text}' for x in items)),
             'results':results,'speedup':results['before']['median_ms']/results['after']['median_ms'],
             'request_speedup':results['before']['median_ms']/results['after_request']['median_ms']}
        rows.append(row); print(json.dumps(row),flush=True)
    report={'origin':'self-created milestone benchmark, not official score','repeats':7,'rows':rows,
            'summary':{'median_speedup':statistics.median(x['speedup'] for x in rows),
                       'minimum_speedup':min(x['speedup'] for x in rows)},'attention':None}
    if args.attention_check:
        import torch
        from types import SimpleNamespace
        from transformers.integrations.sdpa_attention import sdpa_attention_forward
        module=SimpleNamespace(num_key_value_groups=7,is_causal=True)
        attention=[]
        for length in [256,1024,4096]:
            generator=torch.Generator(device='cuda').manual_seed(1119+length)
            q=torch.randn(1,14,length,64,device='cuda',dtype=torch.float16,generator=generator)
            k=torch.randn(1,2,length,64,device='cuda',dtype=torch.float16,generator=generator)
            v=torch.randn(1,2,length,64,device='cuda',dtype=torch.float16,generator=generator)
            outputs={}; measurements={}
            for mode,operation in [('native',sdpa_attention_forward),('expanded',expanded_kv_sdpa)]:
                with torch.inference_mode(): operation(module,q,k,v,None)
                samples=[]; torch.cuda.reset_peak_memory_stats()
                for _ in range(5):
                    torch.cuda.synchronize(); start=time.perf_counter_ns()
                    with torch.inference_mode(): output,_=operation(module,q,k,v,None)
                    torch.cuda.synchronize(); samples.append((time.perf_counter_ns()-start)/1e6)
                outputs[mode]=output
                measurements[mode]={'median_ms':statistics.median(samples),'samples_ms':samples,
                                    'peak_allocated_bytes':torch.cuda.max_memory_allocated()}
            difference=(outputs['native'].float()-outputs['expanded'].float()).abs()
            attention.append({'length':length,'measurements':measurements,
                              'maximum_absolute_difference':difference.max().item(),
                              'mean_absolute_difference':difference.mean().item()})
        report['attention']={'flash_built':torch.backends.cuda.is_flash_attention_available(),'rows':attention,
                             'limitation':'Floating point attention kernels need not be bitwise identical. Functional model evaluation is separate.'}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['summary']),flush=True)


if __name__=='__main__': main()
