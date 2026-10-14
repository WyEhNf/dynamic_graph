"""Frozen whole-type-module closure versus conservative symbol closure."""
import hashlib
import json
import statistics
import time
from pathlib import Path

from transformers import AutoTokenizer

from context_governance.core import Item, govern, render
from context_governance.local_model import ModelTokenCounter
from context_governance.typescript_context import TypeScriptContext


def protected_units(items, dependencies, counter):
    by_id = {item.id: item for item in items}
    required = {item.id for item in items if item.protected}
    pending = list(required)
    while pending:
        for dependency in dependencies.get(pending.pop(), []):
            if dependency not in required:
                required.add(dependency); pending.append(dependency)
    return counter.count(render([item for item in items if item.id in required]))


def main():
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    tokenizer = AutoTokenizer.from_pretrained(root / 'models/Qwen2.5-Coder-7B-Instruct', local_files_only=True, trust_remote_code=False)
    counter = ModelTokenCounter(tokenizer); counter.count('Tokenizer warmup.')
    baseline = root / 'adapters/typescript/research-baseline-v15/worker.mjs'
    candidate = root / 'adapters/typescript/worker.mjs'
    records = []
    with TypeScriptContext(worker_path=baseline) as old, TypeScriptContext() as new:
        for count in [8, 32, 128, 512, 2048]:
            files = {'main.ts': 'import type {Payload} from "./types"; export function run(x:Payload){return x.value*2;}',
                     'types.ts': 'export interface Base {value:number;}\nexport interface Payload extends Base {}\n' +
                                 ''.join(f'export interface Unused{index} {{padding{index}:number;}}\n' for index in range(count))}
            task = 'Return twice the value.'
            analysis = {}
            minimum = {}
            for label, adapter in [('baseline',old), ('candidate',new)]:
                result = adapter.analyze(files, ['main.ts'], use_cache=False)
                items = [Item('task', 'requirement', task, True), *result['items']]
                minimum[label] = protected_units(items, result['dependencies'], counter)
            samples = {'baseline': [], 'candidate': []}; outcomes = {}
            for repeat in range(11):
                for label, adapter in [('baseline',old), ('candidate',new)] if repeat % 2 == 0 else [('candidate',new), ('baseline',old)]:
                    before = time.perf_counter_ns()
                    result = adapter.analyze(files, ['main.ts'], use_cache=False)
                    items = [Item('task', 'requirement', task, True), *result['items']]
                    try:
                        selected = govern(task, items, 650, counter, result['dependencies'], measure_input=False)
                        outcome = {'completed': True, 'selected_ids': [item['id'] for item in selected['selected']],
                                   'actual_context_tokens': selected['metrics']['output_units']}
                    except ValueError as error:
                        outcome = {'completed': False, 'reason': str(error)}
                    elapsed = (time.perf_counter_ns() - before) / 1e6
                    if label in outcomes and outcomes[label] != outcome:
                        raise AssertionError('unstable governance result')
                    outcomes[label] = outcome; samples[label].append(elapsed)
            record = {'unrelated_type_declarations': count, 'source_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
                      'protected_context_tokens': minimum, 'outcomes': outcomes, 'samples_ms': samples,
                      'median_ms': {label: statistics.median(values) for label,values in samples.items()}}
            records.append(record)
            print(json.dumps({'types': count, 'protected_context_tokens': minimum, 'completed': {key:value['completed'] for key,value in outcomes.items()}}), flush=True)
    report = {'origin': 'Synthetic type-only dependencies; real Qwen tokenizer, no model inference', 'budget_context_tokens': 650,
              'records': records, 'wall_seconds': time.perf_counter() - started,
              'baseline_worker_sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(),
              'candidate_worker_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': '11 alternating paired rounds, cache disabled. Timed worker IPC/indexing, Item construction and exact token governance. Protected-token diagnostics outside timer. Baseline over-budget rejection is not a valid output or timing speedup. A separate compiled semantic test checks required types and inherited fields.'}
    (root / 'artifacts/typescript-type-import-v16.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
