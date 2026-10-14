"""Same-source hybrid layout: owned input buffer lifetime only."""
from pathlib import Path
import json,sys
from benchmark_column_workspace import main

if __name__=='__main__':
    main(milestone='input-reuse',variants=('reuse-control','input-reuse'),
         stress_variants=('reuse-control','input-reuse'),stress_queues=('heap',),
         perf_sizes=(1024,2048,4096,10000),perf_threads=(1,4,16),
         stream_threads=(4,16),large_single_repeats=3,
         contract='same runtime/math/ABI/owned API; both COLUMN/ROW/TRANSPOSE/SCANS ON; only REUSE differs; explicit dense consumes A after run joins all workers then +0 upper and complete lower export; full original C bytes; auto/VM/stage retain baseline allocations; compute includes input destruction, upper clearing and export; repeated M lifetime; peak WS/commit and shared host CPU measured')
    if '--phase' in sys.argv and sys.argv[sys.argv.index('--phase')+1]=='stress':
        root=Path(__file__).resolve().parent.parent/'artifacts/input-reuse-milestone'
        report=json.loads((root/'input-reuse-stress-report.json').read_text())
        for r in report['stress']:
            expected=r['matrices'] if r['variant']=='input-reuse' else 0
            if r['selected_engine']!='tiled' or r['input_buffers_reused']!=expected:
                raise AssertionError(('owned reuse dispatch missing',r))
        print('PASS every strict stress matrix exercises expected reuse/fallback')
