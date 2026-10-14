"""Predeclared paired whole-runtime trial; source-order C bytes remain the oracle."""
import hashlib
import json
import statistics
import time
from pathlib import Path
from analyze_source import analyze
from evaluate_source import run_runtime, exact_compare
from research_reference import ensure_dense_reference


def main():
    project = Path(__file__).resolve().parents[1]
    root = project / 'artifacts/stage2-packed-ready'
    output = root / 'performance.json'
    if output.exists():
        raise SystemExit('Refusing to overwrite previous measurements')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    baseline, candidate = root / 'baseline.exe', project / 'build-stage2-packed/cholesky_runtime.exe'
    plan = json.loads((root / 'research-and-plan.json').read_text(encoding='utf-8'))
    assert sha(baseline) == plan['baseline_binary_sha256']
    paths = [project / 'CMakeLists.txt', *sorted((project / 'src').glob('*.cpp')), *sorted((project / 'include').rglob('*.hpp'))]
    hashes = {p.relative_to(project).as_posix(): sha(p) for p in paths}
    for p in paths:
        target = root / 'candidate-source' / p.relative_to(project)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    candidate_copy = root / 'candidate.exe'
    if candidate_copy.exists():
        raise SystemExit('Candidate binary already frozen')
    candidate_copy.write_bytes(candidate.read_bytes())
    candidate = candidate_copy
    started = time.perf_counter()
    configs = [(2048, 4, 32), (4096, 4, 32), (4096, 16, 64), (10000, 4, 64), (10000, 16, 64)]
    report = {'passed': False, 'status': 'running', 'binary_sha256': {'baseline': sha(baseline), 'candidate': sha(candidate)},
              'source_sha256': hashes, 'predeclared_configs': configs, 'repeats': 3,
              'order': 'alternate baseline/candidate by round and configuration; rotate configs by round',
              'contract': 'Full byte-identical actual original-C oracle including headers and signed zero; dense structure forced',
              'concurrency': 'CPU shared with other project work; no claim that medians eliminate interference',
              'records': [], 'references': [], 'summary': []}
    def save():
        report['wall_seconds'] = time.perf_counter() - started
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    try:
        metadata = root / 'page/program.meta'
        analyze(project / 'fixtures/official_naive_transcribed.c', metadata, 'C:/Program Files/LLVM/bin/clang.exe', 'cholesky')
        references = {}
        for n in sorted({c[0] for c in configs}):
            ip, ref, provenance = ensure_dense_reference(project, n, 'E:/mingw64/bin/gcc.exe')
            references[n] = (ip, ref)
            report['references'].append(provenance)
            save()
        for repeat in range(3):
            rotated = configs[repeat:] + configs[:repeat]
            for idx, (n, threads, tile) in enumerate(rotated):
                variants = [('baseline', baseline), ('candidate', candidate)]
                if (repeat + idx) % 2:
                    variants.reverse()
                for label, exe in variants:
                    target = root / 'paired-output.bin'
                    metrics = run_runtime(exe, metadata, references[n][0], target, engine='tiled', tile_size=tile,
                                          threads=threads, simd='auto', ready_queue='heap', structure='dense')
                    check = exact_compare(references[n][1], target)
                    report['records'].append({'n': n, 'threads': threads, 'tile': tile, 'repeat': repeat, 'variant': label, **metrics, **check})
                    save()
                    print(json.dumps({'n': n, 'threads': threads, 'tile': tile, 'repeat': repeat,
                                      'variant': label, 'compute_ms': metrics['compute_ms'], 'bytes_match': True}), flush=True)
                target.unlink()
        for n, threads, tile in configs:
            grouped = {label: [r for r in report['records'] if (r['n'],r['threads'],r['tile'],r['variant']) == (n,threads,tile,label)]
                       for label in ('baseline','candidate')}
            item = {'n': n, 'threads': threads, 'tile': tile}
            for label, rows in grouped.items():
                item[label] = {'median_compute_ms': statistics.median(r['compute_ms'] for r in rows),
                               'range_compute_ms': [min(r['compute_ms'] for r in rows),max(r['compute_ms'] for r in rows)],
                               'median_kernel_ms': statistics.median(r['kernel_ms'] for r in rows),
                               'median_graph_ms': statistics.median(r['graph_ms'] for r in rows)}
            item['compute_ratio_candidate_over_baseline'] = item['candidate']['median_compute_ms'] / item['baseline']['median_compute_ms']
            report['summary'].append(item)
        assert all(sha(project / rel) == value for rel,value in hashes.items()), 'Source changed during trial'
        assert sha(baseline) == report['binary_sha256']['baseline'] and sha(candidate) == report['binary_sha256']['candidate']
        report.update(passed=True, status='complete')
        save()
        print(json.dumps({'passed': True, 'records': len(report['records']), 'summary': report['summary']}), flush=True)
    except BaseException as exc:
        report.update(status='failed', error=repr(exc))
        save()
        raise


if __name__ == '__main__':
    main()
