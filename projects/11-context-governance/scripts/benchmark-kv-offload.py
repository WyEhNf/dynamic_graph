"""One-model paired cache-transfer compatibility; not a code-quality score."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

from context_governance.local_model import LocalModel
from context_governance.prepare_model import verify_snapshot
from context_governance.resources import resource_snapshot

parser=argparse.ArgumentParser()
parser.add_argument('--model',required=True)
parser.add_argument('--output',default='artifacts/kv-offload-compatibility-v20.json')
parser.add_argument('--candidate-source',default='adapters/sdpa/research-v20/local_model.py')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
output=Path(args.output)
if output.exists():raise FileExistsError(output)
output.parent.mkdir(parents=True,exist_ok=True)
source=(root/args.candidate_source).resolve()
spec=importlib.util.spec_from_file_location('context_governance._cache_benchmark_candidate',source)
candidate=importlib.util.module_from_spec(spec);sys.modules[spec.name]=candidate;spec.loader.exec_module(candidate)
started=time.time()
output.write_text(json.dumps({'origin':'Synthetic cache-transfer compatibility; no hidden quality oracle',
    'started_unix':started,'candidate_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'status':'model_loading_and_warmup','cases':[]},indent=2),encoding='utf-8')
model=LocalModel(args.model,'cuda',attention='expanded',prefill_chunk=1024,quantization='nf4')
model.kv_offload_min_tokens=0 # Force CPU offload in this compatibility test only.
captured=[]
original_generate=model.model.generate
def capture_ids(*positional,**kwargs):
    result=original_generate(*positional,**kwargs)
    captured.append(result.detach().cpu().tolist())
    return result
model.model.generate=capture_ids
methods={'resident':LocalModel.generate,'offloaded':candidate.LocalModel.generate}
warm=model.prompt('Warmup.','Return def identity(x): return x.')
for function in methods.values():function(model,warm,16)
captured.clear()
report={'origin':'Synthetic cache-transfer compatibility; no hidden quality oracle',
        'started_unix':started,'candidate_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'baseline_source_sha256':hashlib.sha256((root/'src/context_governance/local_model.py').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model_manifest':model.manifest,'prefill_chunk_tokens':1024,'forced_offload_min_tokens':0,
        'real_candidate_default_min_tokens':16384,'torch_version':model.torch.__version__,'cases':[],
        'scope':'Same loaded model, original expanded SDPA and NF4 weights. Force CPU KV offload below the production-candidate threshold to compare complete greedy token IDs. Two alternating paired rounds; elapsed includes a common CPU token-ID capture wrapper. Allocator peaks reset per call, CPU peak cumulative process-wide. Six synthetic prompts do not establish general engineering code quality.'}
tasks=['Return def identity(x): return x.',
       'Return def twice(x): return x * 2.',
       'Return def sorted_unique(xs): return sorted unique values from xs, without changing xs.']
for count in [64,256]:
    context=''.join(f'def unused_{i}(x): return x + {i}\n' for i in range(count))
    for task in tasks:
        prompt=model.prompt(context,task)
        runs={name:[] for name in methods}
        ids={name:[] for name in methods}
        for repeat in range(2):
            for name in (['resident','offloaded'] if repeat%2==0 else ['offloaded','resident']):
                model.sync();baseline=model.torch.cuda.memory_allocated();model.torch.cuda.reset_peak_memory_stats()
                generation=methods[name](model,prompt,96)
                actual_ids=captured.pop()
                ids[name].append(actual_ids)
                runs[name].append({**asdict(generation),'repeat':repeat,
                                   'complete_token_ids_sha256':hashlib.sha256(json.dumps(actual_ids,separators=(',',':')).encode()).hexdigest(),
                                   'resident_cuda_bytes_before':baseline,'resources':resource_snapshot(model)})
        equal=ids['resident']==ids['offloaded']
        record={'unrelated_functions':count,'public_task':task,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                'exact_complete_greedy_ids_equal':equal,'runs':runs,
                'generation_median_ms':{name:statistics.median(x['elapsed_ms'] for x in group) for name,group in runs.items()}}
        report['cases'].append(record)
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        if not equal:
            raise AssertionError('CPU KV offload changed complete greedy token IDs; failed pair saved')
        print(json.dumps({'count':count,'task':task,'ids_equal':True,'median_ms':record['generation_median_ms']}),flush=True)
report['model_files_verified_at_finalization']=bool(verify_snapshot(args.model))
report['finished_unix']=time.time();report['wall_seconds']=report['finished_unix']-started
output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(report['cases']),'timed_calls':24,'all_complete_greedy_ids_equal':True,'wall_seconds':report['wall_seconds']}))
