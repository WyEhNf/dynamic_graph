"""Paired cold/warm snapshot indexing, including IPC and governance."""
import hashlib
import json
import statistics
import time
from pathlib import Path

from context_governance.core import ByteEstimate, Item, govern
from context_governance.typescript_context import TypeScriptContext


def main():
    records = []
    overall = time.perf_counter()
    with TypeScriptContext() as adapter:
        for count in [32, 128, 512, 2048]:
            for parts in [1, 8]:
                files = {'main.ts': 'import {twice} from "./helper"; export function run(x:number){return twice(x);}',
                         'helper.ts': 'function increment(x:number){return x+1;} export function twice(x:number){return increment(x)*2;}'}
                for part in range(parts):
                    files[f'unrelated{part}.ts'] = ''.join(f'export function unused_{index}(x:number){{return x+{index};}}\n'
                                                           for index in range(part, count, parts))
                source_sha = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
                samples = {'uncached': [], 'cached': []}
                reference = None
                max_resident = 0
                for repeat in range(11):
                    for cache in [False, True] if repeat % 2 == 0 else [True, False]:
                        started = time.perf_counter_ns()
                        result = adapter.analyze(files, ['main.ts'], use_cache=cache)
                        items = [Item('task', 'requirement', 'Preserve run and dependencies.', True), *result['items']]
                        selected = govern('Preserve run and dependencies.', items, 1500, ByteEstimate(), result['dependencies'])
                        elapsed = (time.perf_counter_ns() - started) / 1e6
                        # Verify whole selected source and decisions outside the
                        # timed interval, independent of the cache hit flag.
                        identity = (selected['context'], selected['decisions'], selected['dependency_map'])
                        if reference is None:
                            reference = identity
                        if identity != reference:
                            raise AssertionError('cache changed context, decisions or dependencies')
                        max_resident = max(max_resident, result['worker_resident_bytes'])
                        samples['cached' if cache else 'uncached'].append({'wall_ms': elapsed, 'worker_analysis_ms': result['analysis_ms'],
                                                                        'cache_hit': result['cache_hit']})
                cold = statistics.median(x['wall_ms'] for x in samples['uncached'])
                warm_samples = [x for x in samples['cached'] if x['cache_hit']]
                warm = statistics.median(x['wall_ms'] for x in warm_samples)
                record = {'unrelated_declarations': count, 'unrelated_files': parts,
                          'source_sha256': source_sha, 'utf8_source_bytes': sum(len(x.encode()) for x in files.values()),
                          'selected_code_ids': [x['id'] for x in selected['selected'] if x['kind'] == 'code'],
                          'equivalent_all_22_selections': True, 'samples': samples,
                          'uncached_wall_median_ms': cold, 'cached_wall_median_ms': warm,
                          'speedup': cold / warm, 'maximum_observed_worker_resident_bytes': max_resident}
                records.append(record)
                print(json.dumps({key: record[key] for key in ['unrelated_declarations','unrelated_files','speedup']}), flush=True)
    report = {'origin': 'Synthetic TypeScript compiler indexing; byte budget, not model tokens',
              'compiler_version': '6.0.3', 'records': records,
              'median_speedup': statistics.median(x['speedup'] for x in records),
              'minimum_speedup': min(x['speedup'] for x in records),
              'wall_seconds': time.perf_counter() - overall,
              'scope': 'Timers include Python serialization, worker IPC, snapshot indexing, Item construction and governance. Node startup excluded from samples but included in full batch wall time. Prior snapshots held by this one caller-owned worker; warm hits reuse only identical complete input. 11 paired rounds, first non-hit excluded from warm median and preserved.',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path('artifacts/typescript-context-v15.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['median_speedup','minimum_speedup','wall_seconds']}))


if __name__ == '__main__':
    main()
