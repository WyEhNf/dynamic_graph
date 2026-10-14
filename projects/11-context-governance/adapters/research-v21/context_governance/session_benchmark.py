"""Cold setup versus amortized request timing; verify identical selections."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from .bundles import load_case
from .core import Item, PreparedContext, govern, render
from .local_model import ModelTokenCounter


def main():
    from transformers import AutoTokenizer
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--suite',default='fixtures/engineering-v5')
    parser.add_argument('--output',default='artifacts/research-session-cache-v6.json')
    args=parser.parse_args()
    tokenizer=AutoTokenizer.from_pretrained(args.model,local_files_only=True,trust_remote_code=False)
    counter=ModelTokenCounter(tokenizer); suite=Path(args.suite)
    ids=json.loads((suite/'manifest.json').read_text())['case_ids']; workloads=[]
    for name in ids:
        metadata,_,spec,items=load_case(suite,name)
        workloads.append((name,spec,items,metadata['context_dependencies']))
    for count in [64,256,1024]:
        items=[Item('constraints','requirement','Fix parser invalid integers and preserve errors.',True)]
        items += [Item(f'module-{i}','code',f'def parser_variant_{i}(value):\n    return value+{i}\n'+'# legacy detail 中文说明\n'*8) for i in range(count)]
        deps={f'module-{i}':[f'module-{i-1}'] for i in range(1,count,13)}
        workloads.append((f'wide-{count}','Fix parser invalid integers',items,deps))
    rows=[]
    for name,task,items,deps in workloads:
        start=time.perf_counter_ns(); prepared=PreparedContext(items,deps)
        build_ms=(time.perf_counter_ns()-start)/1e6
        start=time.perf_counter_ns()
        first=govern(task,items,650,counter,deps,False,prepared)
        first_ms=(time.perf_counter_ns()-start)/1e6
        times={'uncached':[],'cached':[]}
        for repeat in range(11):
            order=['uncached','cached'] if repeat%2==0 else ['cached','uncached']
            results={}
            for mode in order:
                start=time.perf_counter_ns()
                result=govern(task,items,650,counter,deps,False,prepared if mode=='cached' else None)
                times[mode].append((time.perf_counter_ns()-start)/1e6)
                results[mode]=result
            for key in ['context','selected','decisions','dependency_map']:
                if results['uncached'][key]!=results['cached'][key]: raise RuntimeError('cached policy changed output')
            selected={x['id'] for x in results['cached']['selected']}
            if counter.count(results['cached']['context'])>650 or any(not set(deps.get(x,[]))<=selected for x in selected):
                raise RuntimeError('independent budget/dependency check failed')
        medians={mode:statistics.median(samples) for mode,samples in times.items()}
        saved=medians['uncached']-medians['cached']
        row={'id':name,'input_tokens':counter.count(render(items)),'index_build_ms':build_ms,
             'first_cached_request_ms':first_ms,'warm_median_ms':medians,'samples_ms':times,
             'warm_speedup':medians['uncached']/medians['cached'],
             'setup_break_even_requests_estimate':None if saved<=0 else (build_ms+first_ms-medians['uncached'])/saved,
             'identical_selection':True,'cold_cost_cache_misses':first['metrics']['fragment_cost_cache_misses']}
        rows.append(row); print(json.dumps(row),flush=True)
    report={'origin':'self-created session-cache milestone, not official score','repeats':11,'rows':rows,
            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
            'summary':{'median_warm_speedup':statistics.median(r['warm_speedup'] for r in rows),
                       'minimum_warm_speedup':min(r['warm_speedup'] for r in rows)},
            'limitations':['Setup is measured separately, not included in warm request time. No global cache; caller retains the session snapshot.',
                           'Exact selected-context token counts are always recomputed; fragment costs only screen candidates.',
                           'Shared CPU machine; alternating order with raw samples retained. No inference in this benchmark.']}
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['summary']),flush=True)


if __name__=='__main__': main()
