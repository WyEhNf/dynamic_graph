"""Cached current waits plus a proven row factor prefix; no kernel changes."""
from benchmark_column_workspace import main
from pathlib import Path
import argparse,json,subprocess,sys
from research_reference import sha256

if __name__=='__main__':
    gate=argparse.ArgumentParser(add_help=False);gate.add_argument('--phase',default='stress');args,_=gate.parse_known_args()
    project=Path(__file__).resolve().parent.parent
    if args.phase=='performance':
        evidence=json.loads((project/'artifacts/lazy-prefix-lifecycle/test-report.json').read_text())
        if not evidence['passed']or evidence['binary_sha256']!=sha256(project/'artifacts/baseline-lazy-prefix-runtime.exe'):raise AssertionError('worker exception lifecycle must pass for this binary')
    main(milestone='lazy-prefix',variants=('thread-policy','lazy-graph','lazy-prefix'),
         stress_variants=('lazy-prefix',),stress_queues=('heap','bucket'),
         perf_threads=(1,4,8,16),perf_sizes=(2048,4096,10000),stream_threads=(4,8,16),
         extra_geometry=((4096,32,(4,16)),(10000,32,(4,16))),
         contract='original-C full bytes; same row-major math/shape/notify; O(t^2) current states; cached factor wait count and monotone factor prefix per row, with runtime ordering invariant; graph bytes include 2*t prefix directory; auto B and forced B32 separate; full process CPU and shared host counters')
    if args.phase=='stress':subprocess.run([sys.executable,str(project/'tools/test_lazy_lifecycle.py'),'--variant','lazy-prefix'],check=True)
