"""Preserve all 69 R31 witness-feasible failures; no case changes or filtering."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    prior=json.loads(Path('reports/final-hard-batch31.json').read_text())
    documents={}
    selected=[]
    for row in prior['failures']:
        path=row['input']
        if path not in documents:
            documents[path]=json.loads(Path(path).read_text())
        matches=[c for c in documents[path]['cases'] if c['name']==row['name']]
        assert len(matches)==1
        selected.append(matches[0])
    assert len(selected)==69
    suite=Path('data/frontier-recovery-batch32.json')
    suite.write_text(json.dumps(dict(format='aicore-local-v1',cases=selected)),encoding='utf-8')
    provenance=dict(record_count=69,source_report='reports/final-hard-batch31.json',source_report_sha256=sha('reports/final-hard-batch31.json'),
        source_inputs={p:sha(p) for p in documents},selection='All 69 old failures, exact case objects and unchanged witness/deadline; no topology or scoring changes',
        suite=str(suite),suite_sha256=sha(suite),solution_sha256=sha('solution/solution.cpp'),exe_sha256=sha('build/aicore_bench.exe'))
    started=time.perf_counter()
    p=subprocess.run(['build/aicore_bench.exe','--input',str(suite),'--output','reports/frontier-recovery-batch32.json','--csv','reports/frontier-recovery-batch32.csv'])
    assert p.returncode in (0,1)
    out=json.loads(Path('reports/frontier-recovery-batch32.json').read_text())
    assert out['summary']['total']==69 and all(c['models_equal'] for c in out['cases'])
    provenance.update(summary=out['summary'],elapsed_wall_seconds=time.perf_counter()-started,
        recovered=[dict(name=c['name'],n=c['n'],T=c['T'],peak=c['peak_memory']) for c in out['cases'] if c['pass']],
        all_solve_us=sum(c['solve_us'] for c in out['cases']),all_thread_cpu_us=sum(c['solve_thread_cpu_us'] for c in out['cases']))
    Path('reports/frontier-recovery-batch32-provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(json.dumps(provenance,indent=2))

if __name__=='__main__':main()
