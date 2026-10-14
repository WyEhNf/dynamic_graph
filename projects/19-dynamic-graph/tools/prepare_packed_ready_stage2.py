"""Freeze the literature-led queue experiment before changing or measuring it."""
import hashlib
import json
import shutil
import time
from pathlib import Path


def main():
    project = Path(__file__).resolve().parents[1]
    root = project / 'artifacts' / 'stage2-packed-ready'
    if root.exists():
        raise SystemExit('Refusing to overwrite a previous experiment')
    root.mkdir()
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    binary = project / 'build/cholesky_runtime.exe'
    expected = json.loads((project / 'artifacts/final-profiles/scale-report.json').read_text())['binary_sha256']['local-mingw']
    if digest(binary) != expected:
        raise RuntimeError('Baseline binary differs from the final verified profile')
    shutil.copy2(binary, root / 'baseline.exe')
    paths = [project / 'CMakeLists.txt', project / 'CMakePresets.json']
    paths += sorted((project / 'src').glob('*.cpp'))
    paths += sorted((project / 'include').rglob('*.hpp'))
    source_hashes = {}
    for path in paths:
        rel = path.relative_to(project)
        target = root / 'baseline-source' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        source_hashes[rel.as_posix()] = digest(path)
    research = {
        'created_unix': time.time(), 'stage': 'literature before implementation and measurement',
        'scope': 'Project 19; improve scheduling cost while retaining every FP64 source operation and exact results',
        'sources': [
            {'title': 'A Scalable High Performant Cholesky Factorization for Multicore with GPU Accelerators',
             'authors': 'Hatem Ltaief, Stanimire Tomov, Rajib Nath, Peng Du, Jack Dongarra',
             'url': 'https://www.netlib.org/lapack/lawnspdf/lawn223.pdf',
             'verified': 'Netlib PDF title, abstract and runtime section read 2026-10-11',
             'transfer': 'Tile DAG granularity and scheduling/locality matter; retain existing parameterized task graph.',
             'boundary': 'GPU BLAS kernels and reduction changes do not establish our source-order bitwise contract.'},
            {'title': 'LAPACK DPOTRF official source',
             'url': 'https://www.netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html',
             'transfer': 'Environment-sensitive block sizing; BLAS3 dependency structure.',
             'boundary': 'Numerical factorization equivalence is weaker than the required byte-identical original C result; do not replace arithmetic with arbitrary BLAS.'},
            {'title': 'StarPU official features', 'url': 'https://starpu.gitlabpages.inria.fr/features.html',
             'transfer': 'Runtime overhead, locality, performance models and task granularity are explicit engineering dimensions.',
             'boundary': 'No StarPU dependency added; heterogeneous/GPU speed claims are not transferable to this laptop.'},
            {'title': 'From Fork-Join to Asynchronous Tasks: Parallelizing Tiled Cholesky Decomposition with OpenMP and HPX',
             'authors': 'Alexander Strack, Alexander Van Craen, Dirk Pflueger', 'date': '2026-06-10',
             'url': 'https://arxiv.org/html/2606.11937v1',
             'transfer': 'The comparison isolates task overhead and unnecessary barriers; consider reducing ready-queue overhead without adding barriers.',
             'boundary': '128-core dual-socket Linux/BLAS experiment, one hardware platform; it does not prove our exact arithmetic or expected speedup.'}
        ],
        'candidate': 'Pack immutable heap priority (column, panel, original task index) into a uint64_t. Avoid repeated random task loads during comparisons; identical ordering and 8-byte heap entries.',
        'proof_obligations': ['Task index fits uint32; task cap is 16 million', 'Column/panel fit uint16 already stored in Task', 'Numeric packed ordering equals old lexicographic comparator including tie-breaking', 'Preserve pending transitions, notifications, execution and all arithmetic'],
        'measurement_plan': {'stress': 'Four actual C sources, FP extremes and odd/tail shapes; independent compiled-C oracle and full output bytes',
                             'queue': 'Independent shuffled synthetic priority orders against tuple sorting; measure actual baseline/candidate comparison operations in one frozen batch',
                             'performance': 'Same-machine alternating original and candidate, dense 2048/4096/10000 and varied threads/tiles; preserve negative groups and exact whole-file results'},
        'default_policy': 'Candidate compile option stays OFF until meaningful end-to-end benefit and correctness are verified',
        'baseline_binary_sha256': expected, 'baseline_source_sha256': source_hashes,
        'no_measurement_yet': True
    }
    (root / 'research-and-plan.json').write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'frozen': str(root), 'sources': len(paths), 'baseline_sha256': expected}))


if __name__ == '__main__':
    main()
