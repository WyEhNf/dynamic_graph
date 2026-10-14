"""Keep source/kernel/tile policy fixed; change only resident DAG scheduling."""
from benchmark_column_workspace import main
from pathlib import Path
import argparse,json,subprocess,sys
from research_reference import sha256

if __name__=='__main__':
    gate=argparse.ArgumentParser(add_help=False);gate.add_argument('--phase',default='stress');args,_=gate.parse_known_args()
    project=Path(__file__).resolve().parent.parent
    if args.phase=='performance':
        evidence=json.loads((project/'artifacts/lazy-graph-lifecycle/test-report.json').read_text())
        if not evidence['passed']or evidence['binary_sha256']!=sha256(project/'artifacts/baseline-lazy-graph-runtime.exe'):raise AssertionError('worker exception lifecycle must pass for this binary')
    main(milestone='lazy-graph',variants=('thread-policy','lazy-graph'),
         stress_variants=('lazy-graph',),stress_queues=('heap','bucket'),
         perf_threads=(1,4,8,16),perf_sizes=(1024,2048,4096,10000),stream_threads=(4,8,16),
         contract='original-C full bytes; one mutable current-panel state per lower target tile; immutable completed factors supply readiness; same row-major kernel, source order, tile shape and notification policy; Q logical executions with O(t^2) resident states; both heap/bucket; CPU counters include full process and other shared host work')
    if args.phase=='stress':subprocess.run([sys.executable,str(project/'tools/test_lazy_lifecycle.py')],check=True)
