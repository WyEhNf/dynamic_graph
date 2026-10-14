"""One predeclared long-input pair: v20 offload versus v23 chunk reclamation."""
import argparse
from dataclasses import asdict
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

from context_governance.local_model import LocalModel
from context_governance.prepare_model import verify_snapshot
from context_governance.resources import resource_snapshot


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--output', default='artifacts/long-kv-token-compatibility-v23.json')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = Path(args.output)
if output.exists():
    raise FileExistsError(output)
source_paths = {name: root / f'adapters/sdpa/research-v{version}/local_model.py'
                for name, version in [('offloaded', 20), ('reclaimed', 23)]}
sources = {name: load_module('context_governance._long_' + name, path)
           for name, path in source_paths.items()}
probe = load_module('_long_capacity_prompt', root / 'scripts/probe-model-capacity.py')
started = time.time()
report = {'origin': 'Same loaded model, one long-input pair, exact complete greedy token IDs',
          'started_unix': started, 'order_predeclared': ['offloaded', 'reclaimed'],
          'repeats_predeclared': 1, 'maximum_prompt_tokens': 32700, 'max_new_tokens': 16,
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'source_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in source_paths.items()},
          'prompt_generator_sha256': hashlib.sha256((root / 'scripts/probe-model-capacity.py').read_bytes()).hexdigest(),
          'scope': 'One synthetic capacity prompt, no engineering quality oracle or repeat stability claim. Same FP16 K/V, NF4 weights, expanded SDPA and chunk1024. Per-call CUDA peaks reset after synchronization/GC/empty_cache; process RAM peak cumulative and not comparable between the two calls. Common CPU complete-ID capture wrapper is included in both generation timings.',
          'runs': []}
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
model = LocalModel(args.model, 'cuda', attention='expanded', prefill_chunk=1024, quantization='nf4')
model.generate(model.prompt('Warmup.', 'Return def identity(x): return x.'), 16)
prompt = probe.make_prompt(model, 32700)
report.update(prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
              actual_prompt_tokens=model.counter.count(prompt), model_manifest=model.manifest)
captured = []
original_generate = model.model.generate


def capture(*positional, **kwargs):
    result = original_generate(*positional, **kwargs)
    captured.append(result.detach().cpu().tolist())
    return result


model.model.generate = capture
complete_ids = {}
for name in report['order_predeclared']:
    gc.collect()
    model.sync()
    model.torch.cuda.empty_cache()
    resident = model.torch.cuda.memory_allocated()
    model.torch.cuda.reset_peak_memory_stats()
    report['in_progress'] = {'method': name, 'started_unix': time.time()}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    generation = sources[name].LocalModel.generate(model, prompt, 16)
    ids = captured.pop()
    complete_ids[name] = ids
    report['runs'].append({'method': name, **asdict(generation),
                          'complete_token_ids_sha256': hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest(),
                          'resident_cuda_bytes_before': resident, 'resources': resource_snapshot(model)})
    report.pop('in_progress')
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'method': name, 'input_tokens': generation.input_tokens,
                      'output_tokens': generation.output_tokens, 'elapsed_ms': generation.elapsed_ms}), flush=True)
report['exact_complete_greedy_ids_equal'] = complete_ids['offloaded'] == complete_ids['reclaimed']
report['model_files_verified_at_finalization'] = bool(verify_snapshot(args.model))
report['finished_unix'] = time.time()
report['wall_seconds'] = report['finished_unix'] - started
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
if not report['exact_complete_greedy_ids_equal']:
    raise AssertionError('Long-window complete token IDs differ; evidence retained')
print(json.dumps({'exact_complete_greedy_ids_equal': True, 'wall_seconds': report['wall_seconds']}))
