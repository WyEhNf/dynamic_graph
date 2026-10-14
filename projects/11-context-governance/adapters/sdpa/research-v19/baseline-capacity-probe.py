"""Measure full-model prefill capacity; this is not a code-quality score."""
import argparse
import gc
import hashlib
import json
import time
from pathlib import Path

from context_governance.local_model import LocalModel
from context_governance.resources import resource_snapshot


def make_prompt(model, maximum):
    lines = [f'def unused_{index}(x): return x + {index}\n' for index in range(maximum)]
    low, high = 0, len(lines)
    while low < high:
        middle = (low + high + 1) // 2
        prompt = model.prompt(''.join(lines[:middle]), 'Return def identity(x): return x. The preceding functions are unrelated context.')
        if model.counter.count(prompt) <= maximum:
            low = middle
        else:
            high = middle - 1
    return model.prompt(''.join(lines[:low]), 'Return def identity(x): return x. The preceding functions are unrelated context.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', default='artifacts/model-capacity-v14.json')
    parser.add_argument('--prompt-tokens', nargs='+', type=int, default=[1024,4096,8192,16384,32700])
    parser.add_argument('--max-new-tokens', type=int, default=16)
    args = parser.parse_args()
    if args.max_new_tokens < 1 or any(length < 128 for length in args.prompt_tokens):
        parser.error('Output limit must be positive and prompt targets at least 128 tokens')
    started = time.time()
    model = LocalModel(args.model, 'cuda', attention='expanded', prompt_policy='concise-v3',
                       prefill_chunk=1024, quantization='nf4')
    model.generate(model.prompt('Warmup.', 'Return def identity(x): return x.'), 16)
    report = {'origin': 'Synthetic capacity probe, no engineering quality inference',
              'started_unix': started, 'model_manifest': model.manifest,
              'prefill_chunk_tokens': 1024, 'weight_quantization': 'nf4',
              'maximum_position_embeddings': model.model.config.max_position_embeddings,
              'max_new_tokens': args.max_new_tokens, 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'module_sha256_at_start': {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__).resolve().parents[1]/'src'/'context_governance').glob('*.py')},
              'runs': [], 'scope': 'All input tokens retained; CUDA peaks reset after cleanup per run. CPU peak is process-wide; loading/warmup and prompt construction excluded from generation latency. Single observations are capacity evidence, not stable performance comparisons.'}
    for maximum in args.prompt_tokens:
        prompt = make_prompt(model, maximum)
        tokens = model.counter.count(prompt)
        gc.collect(); model.torch.cuda.empty_cache(); model.sync()
        baseline = model.torch.cuda.memory_allocated()
        model.torch.cuda.reset_peak_memory_stats()
        item = {'requested_maximum_prompt_tokens': maximum, 'actual_prompt_tokens': tokens,
                'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                'resident_cuda_bytes_before_generation': baseline}
        started_call = time.perf_counter()
        try:
            result = model.generate(prompt, args.max_new_tokens)
            item.update(completed=True, input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                        ttft_ms=result.ttft_ms, generation_elapsed_ms=result.elapsed_ms, output=result.output)
        except model.torch.OutOfMemoryError as error:
            item.update(completed=False, reason='CUDA allocation failed', error=str(error)[:1500])
        item['live_wall_seconds'] = time.perf_counter() - started_call
        item['resources'] = resource_snapshot(model)
        item['incremental_peak_cuda_bytes'] = item['resources']['cuda_peak_allocated_bytes'] - baseline
        report['runs'].append(item)
        report['wall_seconds'] = time.time() - started
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({key: item[key] for key in ['actual_prompt_tokens','completed','live_wall_seconds']}), flush=True)
        gc.collect(); model.torch.cuda.empty_cache()
    report['finished_unix'] = time.time()
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
