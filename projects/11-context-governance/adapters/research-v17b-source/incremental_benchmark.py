"""Edit-to-request cost with fresh versus safely revised immutable indices."""
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
    parser.add_argument('--output',default='artifacts/research-incremental-cache-v10.json')
    args=parser.parse_args()
    counter=ModelTokenCounter(AutoTokenizer.from_pretrained(args.model,local_files_only=True,trust_remote_code=False))
    suite=Path('fixtures/engineering-v5'); workloads=[]
    for name in json.loads((suite/'manifest.json').read_text())['case_ids']:
        metadata,_,spec,items=load_case(suite,name)
        workloads.append((name,spec,items,metadata['context_dependencies']))
    for count in [64,256,1024]:
        items=[Item('constraints','requirement','Fix parser invalid integers and preserve errors.',True)]
        items += [Item(f'module-{i}','code',f'def parser_variant_{i}(value):\n    return value+{i}\n'+'# legacy detail 中文说明\n'*8) for i in range(count)]
        graph={f'module-{i}':[f'module-{i-1}'] for i in range(1,count,13)}
        workloads.append((f'wide-{count}','Fix parser invalid integers',items,graph))
    rows=[]
    for name,task,original,graph in workloads:
        prior=PreparedContext(original,graph)
        govern(task,original,650,counter,graph,False,prior)
        # The same tiny edit is used for both methods. A separate graph change
        # also exercises closure invalidation without an invented dependency.
        changed=next(i for i,item in enumerate(original) if item.kind=='code')
        item=original[changed]
        revised_items=list(original)
        revised_items[changed]=Item(item.id,item.kind,item.text+'\n# edited source revision\n',item.protected,item.utility)
        for graph_mode in ['same_graph','graph_changed']:
            next_graph={key:list(value) for key,value in graph.items()}
            if graph_mode=='graph_changed':
                # Removing a dependency is a changed graph, not a claim that
                # this represents a valid real-program dependency analysis.
                if next_graph: next_graph.pop(next(iter(next_graph)))
                else:
                    next_graph[revised_items[-1].id]=[revised_items[0].id]
            samples={'fresh':[],'revised':[]}; outcomes=[]; misses={}
            for repeat in range(11):
                results={}
                for mode in (['fresh','revised'] if repeat%2==0 else ['revised','fresh']):
                    start=time.perf_counter_ns()
                    index=PreparedContext(revised_items,next_graph) if mode=='fresh' else prior.revised(revised_items,next_graph)
                    try:
                        result=govern(task,revised_items,650,counter,next_graph,False,index)
                        outcome={key:result[key] for key in ['context','selected','decisions','dependency_map']}
                        if counter.count(result['context'])>650: raise AssertionError('budget exceeded')
                        selected={entry['id'] for entry in result['selected']}
                        if any(not set(next_graph.get(node,[]))<=selected for node in selected):
                            raise AssertionError('missing dependency')
                        misses[mode]=result['metrics']['fragment_cost_cache_misses']
                    except ValueError as error:
                        outcome={'explicit_error':str(error)}
                    samples[mode].append((time.perf_counter_ns()-start)/1e6)
                    results[mode]=outcome
                if results['fresh']!=results['revised']: raise AssertionError('incremental revision changes policy')
                outcomes.append('explicit_error' if 'explicit_error' in results['fresh'] else 'selected_context')
            median={mode:statistics.median(values) for mode,values in samples.items()}
            row={'id':name,'edit':graph_mode,'input_tokens':counter.count(render(revised_items)),
                 'edited_items':1,'total_items':len(revised_items),'samples_ms':samples,'median_ms':median,
                 'edit_to_request_speedup':median['fresh']/median['revised'],'identical_selection_or_explicit_error':True,
                 'outcomes':outcomes,'fragment_cost_misses':misses}
            rows.append(row)
            print(json.dumps({'id':name,'edit':graph_mode,'speedup':row['edit_to_request_speedup']}),flush=True)
    report={'origin':'self-created edit-to-request benchmark, not official score','repeats':11,'rows':rows,
            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
            'summary':{'median_speedup':statistics.median(row['edit_to_request_speedup'] for row in rows),
                       'minimum_speedup':min(row['edit_to_request_speedup'] for row in rows),
                       'all_equivalent':True},
            'limitations':['Previous immutable snapshot is already indexed and warmed; its setup cost is excluded and reported separately in the session-cache benchmark.',
                           'Timed scope includes updated index construction and its first governance request; exact acceptance counting remains live.',
                           'Graph edits exercise cache invalidation, not semantic soundness of an external dependency analyzer.',
                           'CPU/shared machine only; no model inference or filesystem incremental parser is implemented.']}
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report['summary']),flush=True)


if __name__=='__main__': main()
